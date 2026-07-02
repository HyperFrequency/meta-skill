# CNN Pattern Recognition — References


### Primary library
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — upstream repo, issues, releases (v2.5+)
- [torchvision on GitHub](https://github.com/pytorch/vision) — Conv2D models and pretrained weights
- [Keras on GitHub](https://github.com/keras-team/keras) — multi-backend (TF / JAX / Torch); for the Conv1D pipeline
- [PyTorch documentation (stable)](https://pytorch.org/docs/stable/) — pinned to v2.5
- [Keras 3 documentation](https://keras.io/) — current 3.x API surface
- [Keras examples directory (time series)](https://keras.io/examples/timeseries/) — Conv1D FCN, EEG, anomaly detection patterns

### Deep-dive docs (specific pages worth bookmarking)
- [`torch.nn.Conv1d`](https://pytorch.org/docs/stable/generated/torch.nn.Conv1d.html) — input shape `(B, C, T)`, dilation, groups; the bar/window orientation gotcha
- [`torch.nn.Conv2d`](https://pytorch.org/docs/stable/generated/torch.nn.Conv2d.html) — for rendered chart pipelines
- [`torch.nn.BatchNorm1d / BatchNorm2d`](https://pytorch.org/docs/stable/generated/torch.nn.BatchNorm1d.html) — running mean/var semantics during eval; the silent bug source in walk-forward pipelines
- [`torch.nn.AdaptiveAvgPool1d`](https://pytorch.org/docs/stable/generated/torch.nn.AdaptiveAvgPool1d.html) — fixed-size head independent of input window length
- [torchvision models reference](https://pytorch.org/vision/stable/models.html) — `resnet18` / `efficientnet` / `mobilenet`; choose by FLOPs vs accuracy budget
- [`keras.layers.Conv1D`](https://keras.io/api/layers/convolution_layers/convolution1d/) — channels-last `(B, T, C)` orientation contrasted with PyTorch
- [Keras time-series classification from scratch](https://keras.io/examples/timeseries/timeseries_classification_from_scratch/) — canonical 1-D FCN walkthrough; the architecture template the snippet above follows
- [Keras EEG signal classification](https://keras.io/examples/timeseries/eeg_signal_classification/) — deeper Conv1D stack, good reference for longer windows
- [PyTorch tutorial: training a classifier](https://pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html) — the 2-D loop the chart-CNN section adapts

### Adjacent / alternative libraries
- [KerasCV](https://github.com/keras-team/keras-cv) — modular pretrained vision models (EfficientNet, YOLOX, RetinaNet) when chart classification crosses into detection
- [timm (PyTorch Image Models)](https://github.com/huggingface/pytorch-image-models) — Ross Wightman's image-model zoo; broader than torchvision, faster to swap backbones
- [tsai](https://github.com/timeseriesAI/tsai) — fastai-style time-series CNNs (InceptionTime, ResCNN, TST); good 1-D baselines beyond plain Conv1D
- [aeon](https://github.com/aeon-toolkit/aeon) — scikit-learn-compatible time-series classifier zoo, includes deep models
- [sktime](https://github.com/sktime/sktime) — broader time-series toolkit; CNN baselines and the canonical UCR/UEA benchmark wrappers

### Academic papers
- LeCun, Y., Bottou, L., Bengio, Y., & Haffner, P. (1998). "Gradient-Based Learning Applied to Document Recognition." *Proceedings of the IEEE* 86(11), 2278-2324. [DOI: 10.1109/5.726791](https://doi.org/10.1109/5.726791) — the LeNet paper; the 2-D CNN ancestor.
- Wang, Z., Yan, W., & Oates, T. (2017). "Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline." *IJCNN 2017*. [arXiv:1611.06455](https://arxiv.org/abs/1611.06455) — FCN / ResNet baselines for 1-D time-series classification; the architecture the Keras example uses.
- Sezer, O. B., & Ozbayoglu, A. M. (2018). "Algorithmic Financial Trading with Deep Convolutional Neural Networks: Time Series to Image Conversion Approach." *Applied Soft Computing* 70, 525-538. [DOI: 10.1016/j.asoc.2018.04.024](https://doi.org/10.1016/j.asoc.2018.04.024) — the chart-image approach for financial CNN classification.
- Bai, S., Kolter, J. Z., & Koltun, V. (2018). "An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling." [arXiv:1803.01271](https://arxiv.org/abs/1803.01271) — TCN paper; argues 1-D CNN beats LSTM on many sequence tasks; relevant to whether to choose CNN over LSTM in this skill.
- Ismail Fawaz, H., Forestier, G., Weber, J., Idoumghar, L., & Muller, P.-A. (2019). "Deep Learning for Time Series Classification: A Review." *Data Mining and Knowledge Discovery* 33(4), 917-963. [DOI: 10.1007/s10618-019-00619-1](https://doi.org/10.1007/s10618-019-00619-1) — definitive survey; benchmarks every 1-D CNN family on UCR archive.

### Tutorials & write-ups
- [PyTorch time-series Conv1D tutorial](https://pytorch.org/tutorials/intermediate/seq2seq_translation_tutorial.html) — adapted Conv1D-based sequence models
- [Keras "Timeseries classification with a Transformer model"](https://keras.io/examples/timeseries/timeseries_classification_transformer/) — direct contrast against the Conv1D pipeline
- [torchinfo on GitHub](https://github.com/TylerYep/torchinfo) — `summary(model, input_size=(B, C, T))`; the right tool for verifying tensor shapes flow correctly through a Conv1D stack

### Standard datasets / benchmarks
- UCR / UEA time-series classification archive — [www.timeseriesclassification.com](http://www.timeseriesclassification.com/) — the canonical TSC benchmark; 128 univariate + 30 multivariate datasets
- Sezer-Ozbayoglu chart-image benchmark (Dow 30, 2007-2017) — used in the original "image conversion approach" paper
- LOBSTER limit order book data — used in `microstructure-analysis` but the standard 1-D CNN evaluation setup for short-horizon prediction

### Last cross-checked
2026-05-20 — via Context7 `/pytorch/pytorch` + `/keras-team/keras-io` + WebSearch verification of all paper DOIs/arXiv IDs.
