import os
import subprocess
import sys
from enum import Enum

import inquirer
from langchain.chains import LLMChain
from langchain.chat_models import ChatLiteLLM
from langchain.llms import LlamaCpp, Ollama
from langchain.prompts import PromptTemplate

from doc_comments_ai import utils


class GptModel(Enum):
    GPT_35 = "gpt-3.5-turbo"
    GPT_35_16K = "gpt-3.5-turbo-16k"
    GPT_4 = "gpt-4"


class LLM:
    def __init__(
        self,
        model: GptModel = GptModel.GPT_35,
        local_model: "str | None" = None,
        azure_deployment: "str | None" = None,
        ollama: "tuple[str,str] | None" = None,
    ):
        max_tokens = 2048 if model == GptModel.GPT_35 else 4096
        if local_model is not None:
            self.install_llama_cpp()

            self.llm = LlamaCpp(
                model_path=local_model,
                temperature=0.8,
                max_tokens=max_tokens,
                verbose=False,
            )
        elif azure_deployment is not None:
            self.llm = ChatLiteLLM(
                temperature=0.8,
                max_tokens=max_tokens,
                model=f"azure/{azure_deployment}",
            )
        elif ollama is not None:
            self.llm = Ollama(
                base_url=ollama[0],
                model=ollama[1],
                temperature=0.8,
                num_ctx=max_tokens,
            )
        else:
            self.llm = ChatLiteLLM(
                temperature=0.8, max_tokens=max_tokens, model=model.value
            )
        self.template = (
            "Act as a {language} language expert. "
            "Add a detailed doc comment to the following {language} method:\n{code}\n"
            "The doc comment should describe what the method does. "
            "{comment_instructions} "
            "Don't include any explanations {haskell_missing_signature}in your response."
        )
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=[
                "language",
                "code",
                "comment_instructions",
                "Haskell_missing_signature",
            ],
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def generate_doc_comment(self, language, code, inline=False, comment_with_source_code=False, docstring=''):
        """
        Generates a doc comment for the given method
        """
        if inline:
            comment_instructions = (
                "Add inline comments to the method body where it makes sense."
                "Return the complete method implementation with the doc comment as a markdown code block. "
                "IMPORTANT: Ensure that absolutely no part of the original function is omitted or modified in your response. Every line, including imports, comments, and variable bindings, should be retained in the output. This is crucial to satisfy my use case."
            )
        elif comment_with_source_code:
            comment_instructions = (
                "Return the complete method implementation with the doc comment as a markdown code block. "
                "IMPORTANT: Ensure that absolutely no part of the original function is omitted or modified in your response. Every line, including imports, comments, and variable bindings, should be retained in the output. This is crucial to satisfy my use case."
            )
            if docstring and len(docstring.strip())>0:
                comment_instructions[0] += 'The following docstring is already provided, please reuse its content as much as possible and revise to reflect any detail that is missing in the existing docstring: '
                comment_instructions[0] += docstring
        else:
            comment_instructions = (
                "Return the doc comment as a markdown block. "
                "If the doc comment consists of more than one sentence then please follow multi-line comments."
                f"IMPORTANT: Please avoid writing any code in the markdown block. Ensure that the markdown block contains only doc comments and enclose them appropriately using the correct comment delimiters for the {language} language."
                """
                Example Comment for Haskell language:
                -- | This is the first line of a demo comment.
                -- This is the second line of a demo comment."
                i.e. Correct comment delimiters for Haskell language is '-- ' where the first line of the comment will be prefixed with '-- | '.
                """
                "Strictly avoid writing detailed comments for self-explanatory functions."
                "IMPORTANT: Strictly refrain from detailing input parameters or specifying what the function takes as input and its definition. This is crucial to meet my use case."
                "IMPORTANT: Please follow only the specified format. This is very important to satisfy my use case."
            )

        if language == "haskell":
            haskell_missing_signature = "and missing type signatures "
        else:
            haskell_missing_signature = ""

        input = {
            "language": language,
            "code": code,
            "comment_instructions": comment_instructions,
            "haskell_missing_signature": haskell_missing_signature,
        }

        documented_code = self.chain.run(input)
        return documented_code

    def install_llama_cpp(self):
        try:
            from llama_cpp import Llama
        except:  # noqa: E722
            question = [
                inquirer.Confirm(
                    "confirm",
                    message=f"Local LLM interface package not found. Install {utils.get_bold_text('llama-cpp-python')}?",
                    default=True,
                ),
            ]

            answers = inquirer.prompt(question)
            if answers and answers["confirm"]:
                import platform

                def check_command(command):
                    try:
                        subprocess.run(
                            command,
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        return True
                    except subprocess.CalledProcessError:
                        return False
                    except FileNotFoundError:
                        return False

                def install_llama(backend):
                    env_vars = {"FORCE_CMAKE": "1"}

                    if backend == "cuBLAS":
                        env_vars["CMAKE_ARGS"] = "-DLLAMA_CUBLAS=on"
                    elif backend == "hipBLAS":
                        env_vars["CMAKE_ARGS"] = "-DLLAMA_HIPBLAS=on"
                    elif backend == "Metal":
                        env_vars["CMAKE_ARGS"] = "-DLLAMA_METAL=on"
                    else:  # Default to OpenBLAS
                        env_vars[
                            "CMAKE_ARGS"
                        ] = "-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"

                    try:
                        subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "pip",
                                "install",
                                "llama-cpp-python",
                            ],
                            env={**os.environ, **env_vars},
                            check=True,
                        )
                    except subprocess.CalledProcessError as e:
                        print(f"Error during installation with {backend}: {e}")

                def supports_metal():
                    # Check for macOS version
                    if platform.system() == "Darwin":
                        mac_version = tuple(map(int, platform.mac_ver()[0].split(".")))
                        # Metal requires macOS 10.11 or later
                        if mac_version >= (10, 11):
                            return True
                    return False

                # Check system capabilities
                if check_command(["nvidia-smi"]):
                    install_llama("cuBLAS")
                elif check_command(["rocminfo"]):
                    install_llama("hipBLAS")
                elif supports_metal():
                    install_llama("Metal")
                else:
                    install_llama("OpenBLAS")

                print("Finished downloading `Code-Llama` interface.")

                # Check if on macOS
                if platform.system() == "Darwin":
                    # Check if it's Apple Silicon
                    if platform.machine() != "arm64":
                        print(
                            "Warning: You are using Apple Silicon (M1/M2) Mac but your Python is not of 'arm64' architecture."
                        )
                        print(
                            "The llama.ccp x86 version will be 10x slower on Apple Silicon (M1/M2) Mac."
                        )
                        print(
                            "\nTo install the correct version of Python that supports 'arm64' architecture visit:"
                            "https://github.com/conda-forge/miniforge"
                        )

            else:
                print("", "Installation cancelled. Exiting.", "")
                return None
