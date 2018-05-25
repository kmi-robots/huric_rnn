"""
Module with functions related to data loading and processing.

IMPORTANT: this file is hard-linked both at /nlu/joint/data.py and at /brain/botcycle/nlu/joint/data.py
"""

import json
import os
import random
import numpy as np

from shutil import copyfile
import xml.etree.ElementTree as ET
from xml.dom import minidom

from spacy.gold import iob_to_biluo, tags_to_entities


def flatten(list_of_lists):
    """Flattens from two-dimensional list to one-dimensional list"""
    return [item for sublist in list_of_lists for item in sublist]

def collapse_multi_turn_sessions(dataset, force_single_turn=False):
    """Turns sessions into lists of messages with previous intent and previous bot turn (words and slot annotations)"""
    sessions = dataset['data']
    dataset['data'] = []
    # hold the previous intent value, initialized to some value (not important)
    previous_intent = dataset['meta']['intent_types'][0]
    previous_bot_turn = []
    previous_bot_slots = []
    intent_changes = []
    for s in sessions:
        for m in s:
            #print('before')
            #print(m)
            if m['turn'] == 'b':
                # this is the bot turn
                previous_bot_turn = m['words']
                previous_bot_slots = m['slots']
            elif m['turn'] == 'u' and m['length']:
                # some sentences are empty
                m['previous_intent'] = previous_intent
                m['bot_turn_actual_length'] = len(previous_bot_turn)
                if force_single_turn != 'no_all' and force_single_turn != 'no_bot_turn':
                    # concatenation of bot words
                    m['words'] = previous_bot_turn + m['words']
                    m['slots'] = previous_bot_slots + m['slots']
                    m['length'] += m['bot_turn_actual_length']
                intent_changes.append(previous_intent != m['intent'])
                if m['intent']:
                    # only append the user sentences with intent
                    dataset['data'].append(m)
                    previous_intent = m['intent']

    print('intent changes: {} over {} samples'.format(sum(intent_changes), len(intent_changes)))
    return dataset

def load_data(dataset_name, mode='measures', slots_type='full'):
    """Loads the dataset and returns it.
    
    if mode='measures' (default), returns [test_data, train_data]
    
    if mode='runtime', returns [None, all the data together], to do a full training to be used at runtime
    
    if mode='finaltest', returns[finaltest, train_data]
        """
    path = 'data/' + dataset_name + '/preprocessed'

    fold_files = os.listdir(path)
    fold_files = sorted([f for f in fold_files if f.startswith('fold_')])

    data_splitted = []
    for file_name in fold_files:
        with open(path + '/' + file_name) as json_file:
            file_content = json.load(json_file)
            if slots_type != 'full':
                file_content = reduce_slots(file_content, slots_type)
            data_splitted.append(file_content)

    if mode == 'measures':
        return data_splitted
    else:
        raise ValueError('mode unsupported:' + mode)

def reduce_slots(file_content, slots_type):
    if slots_type == 'iob_only':
        file_content['meta']['slot_types'] = sorted(set(slots_to_iob_only(file_content['meta']['slot_types'])))
        for sample in file_content['data']:
            sample['slots'] = slots_to_iob_only(sample['slots'])
    elif slots_type == 'slot_only':
        raise NotImplementedError()
    else:
        raise ValueError('{} is not supported'.format(slots_type))

    return file_content

def slots_to_iob_only(slots):
    """takes things like ['O', 'B-Location', 'I-Location'] and returns things like ['O', 'B', 'I']"""
    result = []
    for slot in slots:
        parts = slot.split('-')
        if len(parts) > 1:
            slot = '{}-_'.format(parts[0])
        result.append(slot)
    return result

def adjust_sequences(data, length=50):
    """Fixes the input and output sequences in length, adding padding or truncating if necessary"""
    for sample in data['data']:
        # adjust the sequence of input words
        if len(sample['words']) < length:
            # add <EOS> and <PAD> if sentence is shorter than maximum length
            sample['words'].append('<EOS>')
            while len(sample['words']) < length:
                sample['words'].append('<PAD>')
        else:
            # otherwise truncate and add <EOS> at last position
            sample['words'] = sample['words'][:length]
            sample['words'][-1] = '<EOS>'

        # adjust in the same way the sequence of output slots
        if len(sample['slots']) < length:
            sample['slots'].append('<EOS>')
            while len(sample['slots']) < length:
                sample['slots'].append('<PAD>')
        else:
            sample['slots'] = sample['slots'][:length]
            sample['slots'][-1] = '<EOS>'

    return data


def get_vocabularies(data, meta_data):
    """Collect the input vocabulary, the slot vocabulary and the intent vocabulary"""
    # from a list of training examples, get three lists (columns)
    seq_in = [sample['words'] for sample in data]
    vocab = flatten(seq_in)
    # removing duplicated but keeping the order
    v = ['<PAD>', '<SOS>', '<EOS>'] + vocab
    vocab = sorted(set(v), key=lambda x: v.index(x))
    s = ['<PAD>', '<EOS>'] + meta_data['slot_types']
    slot_tag = sorted(set(s), key=lambda x: s.index(x))
    i = meta_data['intent_types']
    intent_tag = sorted(set(i), key=lambda x: i.index(x))

    return vocab, slot_tag, intent_tag


def get_batch(batch_size, train_data):
    """Returns iteratively a batch of specified size on the data. The last batch can be smaller if the total size is not multiple of the batch"""
    random.shuffle(train_data)
    sindex = 0
    eindex = batch_size
    while sindex < len(train_data):
        batch = train_data[sindex:eindex]
        temp = eindex
        eindex = eindex + batch_size
        sindex = temp
        #print('returning', len(batch), 'samples')
        yield batch

def spacy_wrapper(embedding_size, language, nlp, words_numpy):
    embeddings_values = np.zeros([words_numpy.shape[0], words_numpy.shape[1], embedding_size], dtype=np.float32)
    for j, column in enumerate(words_numpy.T):
        # rebuild the sentence
        words = [w.decode('utf-8') for w in column]
        real_length = words.index('<EOS>')
        # special value for EOS
        embeddings_values[real_length,j,:] = np.ones((embedding_size))
        # remove padding words, embedding values have already been initialized to zero
        words = words[:real_length]
        if language == 'it':
            # TODO handle correctly uppercase/lowercase
            #words = [w.lower() for w in words]
            pass
        # put back together the sentence in order to get the word embeddings with context (only for languages without vectors)
        # TODO skip this if always word vectors, since if word vectors are part of the model, they are fixed and can get them simply by doing lookup
        # unless contextual vectors can be built also when vectors are there
        sentence = ' '.join(words).replace(' \'', '\'')
        if language == 'en' or language == 'it':
            # only make_doc instead of calling nlp, much faster
            doc = nlp.make_doc(sentence)
        else:
            # other languages don't have pretrained word embeddings but use context vectors, really slower
            doc = nlp(sentence)
        # now get the vectors for each token
        for i, w in enumerate(doc):
            if i < real_length:
                if i >= words_numpy.shape[0]:
                    print('out of length', w)
                    print(sentence)
                else:
                    if not w.has_vector:
                        # TODO if oov:
                        #   try lowercase
                        #print('word', w, 'does not have a vector')
                        punctuations = '.?!,;:-_()[]{}\''
                        # TODO handle OOV punctuation marks without special case
                        if language == 'it' and w.text in punctuations:
                            punct_idx = punctuations.index(w.text)
                            embeddings_values[i,j,:] = np.ones((embedding_size))*punct_idx+2
                    else:
                        embeddings_values[i,j,:] = w.vector
                
    return embeddings_values


def get_language_model_name(language, word_embeddings):
    if language == 'en':
        if word_embeddings == 'large':
            return 'en_vectors_web_lg'
        elif word_embeddings == 'small':
            return 'en_core_web_sm'
        elif word_embeddings == 'medium':
            return 'en_core_web_md'
        else:
            raise ValueError('wrong value for word embeddings' + word_embeddings)
    if language == 'it':
        if word_embeddings == 'large':
            return 'it_vectors_wiki_lg'
        elif word_embeddings == 'small':
            return 'it_core_news_sm'
        else:
            raise ValueError('wrong value for word embeddings' + word_embeddings)

    return language


'''the results are not usable at inference time easily, because offsets are in terms of word index, not character ones'''
def sequence_iob_to_ents(iob_sequence):
    """From the sequence of IOB shaped (n_samples, seq_max_len) to label:start-end array"""
    #print(decoder_prediction, intent[0], intent_score)
    # clean up <EOS> and <PAD>
    result = []
    for line in iob_sequence:
        line = [t if (t != '<EOS>' and t != '<PAD>' and t != 0) else 'O' for t in line]
        #print(line)
        line = iob_to_biluo(line)
        entities_offsets = tags_to_entities(line)
        entity_text = ['{}:{}-{}'.format(label, start, end) for (label, start, end) in entities_offsets]
        result.append(entity_text)
    return result

def huric_add_json(out_path, json_preprocessed_list):

    xml_files_list = set([sample['file'] for sample in json_preprocessed_list])
    # load all xml files
    xml_trees = {}
    for xml_file_name in xml_files_list:
        xml_trees[xml_file_name] = ET.parse('{}/{}'.format(out_path, xml_file_name))

    # append the json for each sample
    for sample in json_preprocessed_list:
        xml_file_name = sample['file']
        id = sample['id']
        frame_semantics = xml_trees[xml_file_name].getroot().find('semantics/frameSemantics')
        nn_frame = ET.SubElement(frame_semantics, 'nnFrame', {'id': str(id)})
        nn_frame.text = json.dumps(sample)

    # write the new xml files
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    for xml_file_name in xml_files_list:
        xml_trees[xml_file_name].write('{}/{}'.format(out_path, xml_file_name), encoding='utf-8', xml_declaration=True)

def save_predictions(out_path, fold_number, samples):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    with open('{}/prediction_fold_{}.json'.format(out_path, fold_number), 'w') as outfile:
        json.dump({'samples': samples}, outfile, indent=2)

def merge_prediction_folds(epoch_path):
    fold_files = [f for f in os.listdir(epoch_path) if f.startswith('prediction_fold_')]
    results = []
    for file_name in fold_files:
        with open('{}/{}'.format(epoch_path, file_name), 'r') as f:
            content = json.load(f)
            results.extend(content['samples'])
    
    return results
    
def copy_huric_xml_to(destination):
    xml_folder = 'data/huric_eb/modern/source'
    if not os.path.exists(destination):
        os.makedirs(destination)
    
    files = os.listdir(xml_folder)

    for file_name in files:
        copyfile('{}/{}'.format(xml_folder, file_name), '{}/{}'.format(destination, file_name))

