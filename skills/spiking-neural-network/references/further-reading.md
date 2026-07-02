# SNN references and further reading

## Primary library
- [norse/norse on GitHub](https://github.com/norse/norse) — upstream repo, issues, releases
- [norse documentation](https://norse.github.io/norse/) — pinned to current main as of cross-check
- [jeshraghian/snntorch on GitHub](https://github.com/jeshraghian/snntorch) — alternative library; bigger tutorial set
- [snntorch documentation](https://snntorch.readthedocs.io/) — pinned to v0.9
- [snntorch tutorials directory](https://github.com/jeshraghian/snntorch/tree/master/examples) — quickstart, CNN, LSTM-equivalent (`Synaptic`), recurrent SNNs
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — the autograd substrate both libraries sit on

## Deep-dive docs (specific pages worth bookmarking)
- [norse `lif_step` source](https://github.com/norse/norse/blob/main/norse/torch/functional/lif.py) — the canonical Euler-step LIF; read once to know what `tau_mem_inv`, `v_th`, `v_reset` actually do
- [norse `LIFParameters` dataclass](https://github.com/norse/norse/blob/main/norse/torch/functional/lif.py) — the override surface for membrane dynamics
- [norse module API](https://norse.github.io/norse/auto_api/norse.torch.module.html) — `LIFCell`, `LICell`, `SequentialState` for module-based composition
- [snntorch `Leaky` API](https://snntorch.readthedocs.io/en/latest/snntorch.html#snntorch.Leaky) — `beta`, `spike_grad`, `init_hidden`, `output`; the object-oriented neuron
- [snntorch `Synaptic` API](https://snntorch.readthedocs.io/en/latest/snntorch.html#snntorch.Synaptic) — two-state neuron with synaptic current; closer to bio LIF
- [snntorch `surrogate` module](https://snntorch.readthedocs.io/en/latest/snntorch.surrogate.html) — `fast_sigmoid(slope=25)`, `atan()`, `straight_through_estimator()`
- [snntorch `spikegen` encoding](https://snntorch.readthedocs.io/en/latest/snntorch.spikegen.html) — `rate`, `latency`, `delta` encoders; what each method does to input distribution
- [snntorch quickstart notebook (CNN-SNN)](https://github.com/jeshraghian/snntorch/blob/master/examples/quickstart.ipynb) — surrogate-gradient training end to end

## Adjacent / alternative libraries
- [Brian2](https://github.com/brian-team/brian2) — full computational neuroscience simulator; bigger learning curve but the reference for biological accuracy
- [BindsNET](https://github.com/BindsNET/bindsnet) — PyTorch-based SNN library focused on STDP and biologically plausible learning rules
- [Nengo](https://github.com/nengo/nengo) — neural compiler with built-in Loihi / SpiNNaker backends; relevant when neuromorphic hardware is the deployment target
- [Lava (Intel)](https://github.com/lava-nc/lava) — Intel's open-source neuromorphic computing framework; native for Loihi 2 deployment
- [Spyx (JAX-based SNNs)](https://github.com/kmheckel/spyx) — JAX backend, faster than norse for short networks
- [Auryn](https://github.com/fzenke/auryn) — C++ HPC SNN simulator; reference for large-scale Friedemann Zenke / spike-timing experiments

## Academic papers
- Eshraghian, J. K., Ward, M., Neftci, E., Wang, X., Lenz, G., Dwivedi, G., Bennamoun, M., Jeong, D. S., & Lu, W. D. (2023). "Training Spiking Neural Networks Using Lessons From Deep Learning." *Proceedings of the IEEE* 111(9), 1016-1054. [DOI: 10.1109/JPROC.2023.3308088](https://doi.org/10.1109/JPROC.2023.3308088) / [arXiv:2109.12894](https://arxiv.org/abs/2109.12894) — the snntorch reference paper; serves as a tutorial.
- Neftci, E. O., Mostafa, H., & Zenke, F. (2019). "Surrogate Gradient Learning in Spiking Neural Networks." *IEEE Signal Processing Magazine* 36(6), 51-63. [arXiv:1901.09948](https://arxiv.org/abs/1901.09948) — the conceptual foundation for `fast_sigmoid` / `atan` surrogate gradients.
- Pfeiffer, M., & Pfeil, T. (2018). "Deep Learning With Spiking Neurons: Opportunities and Challenges." *Frontiers in Neuroscience* 12, 774. [DOI: 10.3389/fnins.2018.00774](https://doi.org/10.3389/fnins.2018.00774) — survey of how deep-learning techniques map onto SNNs.
- Davies, M., Srinivasa, N., Lin, T.-H., Chinya, G., Cao, Y., Choday, S. H., et al. (2018). "Loihi: A Neuromorphic Manycore Processor with On-Chip Learning." *IEEE Micro* 38(1), 82-99. [DOI: 10.1109/MM.2018.112130359](https://doi.org/10.1109/MM.2018.112130359) — Intel Loihi paper; relevant if hardware is the deployment target.
- Maass, W. (1997). "Networks of Spiking Neurons: The Third Generation of Neural Network Models." *Neural Networks* 10(9), 1659-1671. [DOI: 10.1016/S0893-6080(97)00011-7](https://doi.org/10.1016/S0893-6080(97)00011-7) — the theoretical motivation for SNNs; "third generation" framing.
- Wu, Y., Deng, L., Li, G., Zhu, J., & Shi, L. (2018). "Spatio-Temporal Backpropagation for Training High-Performance Spiking Neural Networks." *Frontiers in Neuroscience* 12, 331. [DOI: 10.3389/fnins.2018.00331](https://doi.org/10.3389/fnins.2018.00331) — STBP; the BPTT-over-spikes training algorithm both libraries implement.

## Tutorials & write-ups
- [snntorch tutorial series (5-part)](https://snntorch.readthedocs.io/en/latest/tutorials/index.html) — covers spike encoding, LIF, surrogate gradients, regression, CNN
- [Friedemann Zenke "spytorch" tutorial](https://github.com/fzenke/spytorch) — the original surrogate-gradient pedagogical reference; smaller and more focused than snntorch's tutorials
- [Norse "From DNN to SNN" tutorial](https://norse.github.io/norse/auto_examples/index.html) — converting a trained dense net into an equivalent SNN; useful when SNN training from scratch fails

## Standard datasets / benchmarks
- [NMNIST (Neuromorphic MNIST)](https://www.garrickorchard.com/datasets/n-mnist) — MNIST converted to event streams via saccadic camera; the "Hello, World" of neuromorphic vision
- [DVS Gesture](https://research.ibm.com/interactive/dvsgesture/) — IBM gesture recognition; standard event-camera benchmark
- [SHD (Spiking Heidelberg Digits)](https://compneuro.net/datasets/) — speech-to-spike benchmark; the audio analog of NMNIST
- [N-Caltech101](https://www.garrickorchard.com/datasets/n-caltech101) — Caltech-101 converted to event stream
- For finance: no canonical SNN dataset exists; rate-encode OHLCV windows or use trade-arrival timestamps directly as event streams

## Last cross-checked
2026-05-20 — via Context7 `/jeshraghian/snntorch` (1618 snippets, High, benchmark 84.7) + WebSearch verification of all paper DOIs/arXiv IDs.
