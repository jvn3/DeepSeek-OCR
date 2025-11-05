<!-- markdownlint-disable first-line-h1 -->
<!-- markdownlint-disable html -->
<!-- markdownlint-disable no-duplicate-header -->


<div align="center">
  <img src="assets/logo.svg" width="60%" alt="DeepSeek AI" />
</div>


<hr>
<div align="center">
  <a href="https://www.deepseek.com/" target="_blank">
    <img alt="Homepage" src="assets/badge.svg" />
  </a>
  <a href="https://huggingface.co/deepseek-ai/DeepSeek-OCR" target="_blank">
    <img alt="Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-DeepSeek%20AI-ffc107?color=ffc107&logoColor=white" />
  </a>

</div>

<div align="center">

  <a href="https://discord.gg/Tc7c45Zzu5" target="_blank">
    <img alt="Discord" src="https://img.shields.io/badge/Discord-DeepSeek%20AI-7289da?logo=discord&logoColor=white&color=7289da" />
  </a>
  <a href="https://twitter.com/deepseek_ai" target="_blank">
    <img alt="Twitter Follow" src="https://img.shields.io/badge/Twitter-deepseek_ai-white?logo=x&logoColor=white" />
  </a>

</div>



<p align="center">
  <a href="https://huggingface.co/deepseek-ai/DeepSeek-OCR"><b>📥 Model Download</b></a> |
  <a href="https://github.com/deepseek-ai/DeepSeek-OCR/blob/main/DeepSeek_OCR_paper.pdf"><b>📄 Paper Link</b></a> |
  <a href="https://arxiv.org/abs/2510.18234"><b>📄 Arxiv Paper Link</b></a> |
</p>

<h2>
<p align="center">
  <a href="">DeepSeek-OCR: Contexts Optical Compression</a>
</p>
</h2>

<p align="center">
<img src="assets/fig1.png" style="width: 1000px" align=center>
</p>
<p align="center">
<a href="">Explore the boundaries of visual-text compression.</a>       
</p>

## Release
- [2025/10/23]🚀🚀🚀 DeepSeek-OCR is now officially supported in upstream [vLLM](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html#installing-vllm). Thanks to the [vLLM](https://github.com/vllm-project/vllm) team for their help.
- [2025/10/20]🚀🚀🚀 We release DeepSeek-OCR, a model to investigate the role of vision encoders from an LLM-centric viewpoint.

## Contents
- [Project Structure](#project-structure)
- [Quick Start with VS Code Tasks](#quick-start-with-vs-code-tasks)
- [Install](#install)
- [vLLM Inference](#vllm-inference)
- [Transformers Inference](#transformers-inference)

## Project Structure

```
DeepSeek-OCR/
├── app/                              # Backend application
│   ├── ocr_server.py                # FastAPI OCR server
│   ├── simple_server.py             # Mock server for testing
│   ├── requirements.txt             # Python dependencies
│   ├── scripts/                     # Backend utility scripts
│   ├── DeepSeek-OCR-master/        # DeepSeek OCR model files
│   └── vllm-*.whl                  # vLLM wheel file
├── ocr-studio/                      # Next.js frontend application
│   ├── app/                        # Next.js 15 app router
│   ├── components/                 # React components
│   ├── lib/                        # Utilities and API client
│   └── public/                     # Static assets
├── venv/                           # Python virtual environment
├── .vscode/                        # VS Code configuration
│   └── tasks.json                  # Automated tasks
└── README.md
```

## Quick Start with VS Code Tasks

This project includes VS Code tasks for easy development. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) and type "Tasks: Run Task" to see all available tasks:

### Available Tasks

1. **Install All Dependencies** - Install both backend and frontend dependencies
2. **Install Backend Dependencies** - Install Python packages for the OCR backend
3. **Install Frontend Dependencies** - Install npm packages for the Next.js frontend
4. **Run Full Stack (Backend + Frontend)** ⭐ - Run both servers simultaneously (default build task)
5. **Run Backend Server** - Start the OCR backend server (port 8000)
6. **Run Frontend Dev Server** - Start the Next.js dev server (port 3000)
7. **Build Frontend for Production** - Build optimized frontend bundle
8. **Kill Backend Server** - Stop the OCR backend
9. **Kill All Servers** - Stop all running servers

### Running the Full Stack

**Option 1: Using VS Code Tasks (Recommended)**
```
1. Press Ctrl+Shift+B (or Cmd+Shift+B on Mac) - runs "Run Full Stack" by default
2. Or press Ctrl+Shift+P → "Tasks: Run Task" → "Run Full Stack (Backend + Frontend)"
3. Access the application at http://localhost:3000
4. Backend API available at http://localhost:8000

Note: First time will auto-create conda environment at workspace/venv
```

**Option 2: Manual Start**

Backend:
```bash
conda activate ./venv
cd app
python ocr_server.py
```

Frontend:
```bash
cd ocr-studio
npm run dev
```
  




## Install
>Our environment is cuda11.8+torch2.6.0.
1. Clone this repository and navigate to the DeepSeek-OCR folder
```bash
git clone https://github.com/deepseek-ai/DeepSeek-OCR.git
```
2. Conda
```Shell
conda create -n deepseek-ocr python=3.12.9 -y
conda activate deepseek-ocr
```
3. Packages

- download the vllm-0.8.5 [whl](https://github.com/vllm-project/vllm/releases/tag/v0.8.5) 
```Shell
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
wget https://github.com/vllm-project/vllm/releases/download/v0.8.5/vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
pip install -r requirements.txt
pip install flash-attn==2.7.3 --no-build-isolation
```
**Note:** if you want vLLM and transformers codes to run in the same environment, you don't need to worry about this installation error like: vllm 0.8.5+cu118 requires transformers>=4.51.1

## vLLM-Inference
- VLLM:
>**Note:** change the INPUT_PATH/OUTPUT_PATH and other settings in the app/DeepSeek-OCR-master/DeepSeek-OCR-vllm/config.py
```Shell
cd app/DeepSeek-OCR-master/DeepSeek-OCR-vllm
```
1. image: streaming output
```Shell
python run_dpsk_ocr_image.py
```
2. pdf: concurrency ~2500tokens/s(an A100-40G)
```Shell
python run_dpsk_ocr_pdf.py
```
3. batch eval for benchmarks
```Shell
python run_dpsk_ocr_eval_batch.py
```

**[2025/10/23] The version of upstream [vLLM](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html#installing-vllm):**

```shell
uv venv
source .venv/bin/activate
# Until v0.11.1 release, you need to install vLLM from nightly build
uv pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly
```

```python
from vllm import LLM, SamplingParams
from vllm.model_executor.models.deepseek_ocr import NGramPerReqLogitsProcessor
from PIL import Image

# Create model instance
llm = LLM(
    model="deepseek-ai/DeepSeek-OCR",
    enable_prefix_caching=False,
    mm_processor_cache_gb=0,
    logits_processors=[NGramPerReqLogitsProcessor]
)

# Prepare batched input with your image file
image_1 = Image.open("path/to/your/image_1.png").convert("RGB")
image_2 = Image.open("path/to/your/image_2.png").convert("RGB")
prompt = "<image>\nFree OCR."

model_input = [
    {
        "prompt": prompt,
        "multi_modal_data": {"image": image_1}
    },
    {
        "prompt": prompt,
        "multi_modal_data": {"image": image_2}
    }
]

sampling_param = SamplingParams(
            temperature=0.0,
            max_tokens=8192,
            # ngram logit processor args
            extra_args=dict(
                ngram_size=30,
                window_size=90,
                whitelist_token_ids={128821, 128822},  # whitelist: <td>, </td>
            ),
            skip_special_tokens=False,
        )
# Generate output
model_outputs = llm.generate(model_input, sampling_param)

# Print output
for output in model_outputs:
    print(output.outputs[0].text)
```
## Transformers-Inference
- Transformers
```python
from transformers import AutoModel, AutoTokenizer
import torch
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '0'
model_name = 'deepseek-ai/DeepSeek-OCR'

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(model_name, _attn_implementation='flash_attention_2', trust_remote_code=True, use_safetensors=True)
model = model.eval().cuda().to(torch.bfloat16)

# prompt = "<image>\nFree OCR. "
prompt = "<image>\n<|grounding|>Convert the document to markdown. "
image_file = 'your_image.jpg'
output_path = 'your/output/dir'

res = model.infer(tokenizer, prompt=prompt, image_file=image_file, output_path = output_path, base_size = 1024, image_size = 640, crop_mode=True, save_results = True, test_compress = True)
```
or you can
```Shell
cd app/DeepSeek-OCR-master/DeepSeek-OCR-hf
python run_dpsk_ocr.py
```
## Support-Modes
The current open-source model supports the following modes:
- Native resolution:
  - Tiny: 512×512 （64 vision tokens）✅
  - Small: 640×640 （100 vision tokens）✅
  - Base: 1024×1024 （256 vision tokens）✅
  - Large: 1280×1280 （400 vision tokens）✅
- Dynamic resolution
  - Gundam: n×640×640 + 1×1024×1024 ✅

## Prompts examples
```python
# document: <image>\n<|grounding|>Convert the document to markdown.
# other image: <image>\n<|grounding|>OCR this image.
# without layouts: <image>\nFree OCR.
# figures in document: <image>\nParse the figure.
# general: <image>\nDescribe this image in detail.
# rec: <image>\nLocate <|ref|>xxxx<|/ref|> in the image.
# '先天下之忧而忧'
```


## Visualizations
<table>
<tr>
<td><img src="assets/show1.jpg" style="width: 500px"></td>
<td><img src="assets/show2.jpg" style="width: 500px"></td>
</tr>
<tr>
<td><img src="assets/show3.jpg" style="width: 500px"></td>
<td><img src="assets/show4.jpg" style="width: 500px"></td>
</tr>
</table>


## Acknowledgement

We would like to thank [Vary](https://github.com/Ucas-HaoranWei/Vary/), [GOT-OCR2.0](https://github.com/Ucas-HaoranWei/GOT-OCR2.0/), [MinerU](https://github.com/opendatalab/MinerU), [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [OneChart](https://github.com/LingyvKong/OneChart), [Slow Perception](https://github.com/Ucas-HaoranWei/Slow-Perception) for their valuable models and ideas.

We also appreciate the benchmarks: [Fox](https://github.com/ucaslcl/Fox), [OminiDocBench](https://github.com/opendatalab/OmniDocBench).

## Citation

```bibtex
@article{wei2025deepseek,
  title={DeepSeek-OCR: Contexts Optical Compression},
  author={Wei, Haoran and Sun, Yaofeng and Li, Yukun},
  journal={arXiv preprint arXiv:2510.18234},
  year={2025}
}
