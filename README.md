# Applying Naive Bayes to N-Grams for Markov Chain Generation / Text Prediction

*Disclaimer: the code in this notebook is excerpted from the source code and is functional in and of itself; access the source code [here](https://github.com/duncanmazza/ml_ngrams).*

## Introduction and Mathematical Definitions
Many text prediction models utilize some implementation of a n-gram model where consecutive sequences of words of a specified length n in a text can used to predict the next word in a sequence. In this project, I sought to implement a n-gram-like model that utilizes a continuously generated rolling sequence of words and a graph of the directional distances between words to encode n-grams rather than explicitly use n-grams themselves. My implementation was heavily based on the work of Henrique X. Goulart, Mauro D. L. Tosi, Daniel Soares-Gonc ̧ alves, and Rodrigo F. Maiaand Guilherme Wachs-Lopes in their paper "Hybrid Model For Word Prediction Using NaiveBayes and Latent Information"[1], although significant modifications were made to appropriately scope my implementation for the weeklong project.

In the paper, the authors present a method of text prediction that combines  latent semantic analysis (LSA) and naive Bayes along with an algorithm to optimze model hyperparameters to achieve an error rate far lower than LSA or naive Bayes alone. I chose to implement my own variation of just the naive Bayes portion of their model.

### Naive Bayes Graph
Following the definition in [1], there exists a set of directional graphs $`\{ G_0, G_1, ..., G_{d-1} \}`$ for a vector of words $`\mathbf{V}=[w_1, w_2, ..., w_d]^T`$ where the vocabulary $`\mathbf{V}_v`$ is given by $`set(\mathbf{V})`$ and the nodes of graph are comprised by the vocabulary. The directional edges in graph $`G_i`$ between the nodes are positive integer values that represent the number of occurances of the parent node at distance $`i`$ from the child node in the text.

For example, in the text:
``` 
the quick brown fox jumped over the lazy dog the quick cat did not jump over the lazy dog
```
there is a distance 0 from parent node `the` to child node `quick`, and this occurs twice in the text; therefore, in graph $`G_0`$, the edge from `the` to `quick` has a value of 2. For another example, there is a distance 1 between parent node `jump` and child node `the` that occurs twice in the text; therefore, the edge from `jump` to `the` in graph $`G_1`$ has a value of 2. The utilization of this graph is discussed in the next section; following is the description of how I created it.

As a step of pre-processing for the text passed into my model, I generated and cached (in RAM) a list of graphs $`[G_0, G_1, ..., G_{max\_chain}]`$ where `max_chain` is a model parameter (discussed later). These graphs are stored as 2-dimensional square sparse matrices $`\mathbf{M}`$ of type `scscipy.sparse.dok_matrix` (dictionary of keys based sparse matrix), where indices $`(i, j)`$ correspond to a pair of vocabulary words $`(V_{v_i}, V_{v_j})`$; a dictionary called `vocab_to_matrix` stores the vocabulary words' respective index values. The matching of a vocabulary word to an index value is arbitrary as long as it is consistent across both axes and all graphs. Two nested for-loops iterate over a list of all words in $`\mathbf{V}`$ and over windows of size `max_chain`.
