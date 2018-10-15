# Configurations

## Meaning of each parameter

- `LABEL_EMB_SIZE`: the size of the embeddings for the labels. Although the labels of the decoder are outputs, they are used as input too when doing the output dependencies (the label of the previous timestep is fed to the decoder together with the current timestep input). Type: `int`
- `LSTM_SIZE`: the number of units of the LSTM cells. Type: `int`
- `BATCH_SIZE`: the size of the train/test batch. For training this is useful to define the minibatches. Type: `int`
- `OUTPUT_FOLDER`: the results will go in `nlunetwork/results/OUTPUT_FOLDER/` + a folder name for the configuration. Type: `string`
- `DATASET`: use one of the folder names in [the data directory](/data). It must contain a `preprocessed` subfolder with inside the preprocessed fold files with our representation. Type: `string`
- `MODE`: switches the behaviour of test/train/.... Possible values:
  - `dev_cross` that excludes the last fold and performs (k-1)-fold, last fold untouched
  - `cross` that performs k-fold
  - `cross_nested`
  - `eval` that does the train on k-1 and test on last (untouched fold)
  - `train_all` trains the network on all the folds
  - `test` takes a pretrained model (path default or `MODEL_PATH`) and runs it on the specified samples (default or `TEST_PATH`)
  - 'test_all' takes a pretrained model (path default or `MODEL_PATH`) and runs it on the specified samples (default or `TEST_PATH`)
- `MODEL_PATH`: when using `MODE=test` or `MODE=test_all`, the MODEL_PATH is the path to the saved model to be used for inference
- `RECURRENT_MULTITURN` the type of multiturn modeling. It will be used only if in the dataset is marked as multiturn in its metadata. Possible values:
  - `lstm`: uses a LSTM cell (the work presented in [HQA2018](https://doi.org/10.1145/3184558.3191539))
  - `gru`: uses a GRU cell instead of a LSTM
  - `crf`: uses a CRF with two timesteps: previous turn and current turn
- `FORCE_SINGLE_TURN`: as the previous parameter, this only works with multiturn datasets. This options can change the configuration of the multiturn approach by turning on and off the two differences of the multiturn with respect to the single-turn: 1) concatenation of input words with the previous sentence generated by the bot, 2) usage of the previous intent value to use in the top level RNN in the hierarchical structure. See the [HQA paper](https://doi.org/10.1145/3184558.3191539) for details. The possible values are
  - `no_all`: the network is built by discarding the multiturn informations (single-turn, both previous intent and bot words are discarded)
  - `no_bot_turn`: only the previous intent is added, while the words by the bot are discarded
  - `no_previous_intent`: only the words of the bot are added, while the previous intent is discarded
- `LOSS_SUM`: specifies which parts to be used for the overall loss computation (and therefore minimization). Possible values:
  - `both`: both the intent loss and slots loss are used
  - `intent`: only the loss of the intent is used
  - `slots`: only the loss of the slots is used
- `SLOTS_TYPE`: which part of the slots to be considered. Slots are made up of a first part indicating the IOB tag, followed by a dash and then the slot type. This option changes the inputs in the following way:
  - `full`: consider the full slot information (both IOB and type)
  - `iob_only`: only the IOB tag is used, the type is removed
  - `type_only`: only the type is used, discarding the IOB
- `WORD_EMBEDDINGS`: the size/type of the word embeddings to be used to load the corresponding SpaCy model. Look at the function `get_language_model_name` in the file [data.py](/nlunetwork/data.py) for how it is used:
  - `random`: randomly initialized word embeddings will be used. Suggested only for big corpora
  - `large`: huge and more accurate
  - `small`: very small dictionary coverage
  - `medium`: metriotes
- `RECURRENT_CELL`: the type of recurrent cell used in the different layers. Possible values:
  - `lstm`
  - `gru`
- `ATTENTION`: where to use attention layer. Possible values:
  - `intents`: use attention in the intent network only
  - `slots`: use attention in the slots network (for 3L configuration means in both BD and AC)
  - `both`: use attention everywhere
  - `none`: don't use attention at all
- `THREE_STAGES`: switches between 2 layers and 3 layers. The difference is whether BD and AC tasks are performed together or not. Possible values:
  - `false`: use 2 layers only. BD and AC are performed together in a single decoder
  - `true`: use 3 layers. There is one decoder for BD and one decoder for AC
  - `true_highway`: use 3 layers and also enable the highway from encoder to AC decoder
- `INTENT_EXTRACTION_MODE`: how to extract the intent from the encoder. This option only works if the attention on the intents is enabled. Possible values:
  - `bi-rnn`: the attention is applied on top of the bi-rnn outputs at each timestep
  - `word-emb`: the attention is applied on top of word embeddings directly, without bidirectional RNN

## How to use

TODO