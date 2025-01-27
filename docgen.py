from doc_comments_ai import app
import argparse
import sys
import os

def main():
    app.run()

def iterate_files(folder_path):
    file_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Documentation generation master script')
    parser.add_argument('-p', '--path', help="Absolute path to codebase folder for which documentation must be generated")
    parser.add_argument(
        "--ollama-model",
        type=str,
        help="Ollama model for base url",
    )
    parser.add_argument(
        "--ollama-base-url",
        type=str,
        default="http://srsw.cdot.in:11434",
        help="Ollama base url",
    )

    parser.add_argument(
        "--comment_with_source_code",
        action="store_true",
        help="Generates comments with code included. (default - It generates only comment.)"
    )

    parser.add_argument(
        "--line_threshold",
        default=3,
        type=int,
        help="Generate comments for functions with length longer than the specified threshold (default: 3)."
    )

    parser.add_argument(
        "--regenerate_docstring",
        default=False,
        action="store_true",
        help="Rewrite docstrings if they already exist and need update"
    )
    
    args = parser.parse_args()

    folder = args.path
    if not os.path.exists(folder):
        print("Please verify the folder path")
        exit(0)
    # Example usage
    files = iterate_files(folder)

    #Remove the kwargs for path from the sys.argv
    index = 0
    del_index = -1
    for args in sys.argv:
        if args == '-p' or args == '--path':
            del_index = index
            break
        index += 1
    
    if del_index > 0:
        del sys.argv[del_index+1]
        del sys.argv[del_index]
    
    first = True
    for filepath in files:
        if filepath.endswith('.c') or filepath.endswith('.py'):
        #if filepath[-2:]=='.c':
            print(filepath)
            if first:
                sys.argv.append(filepath)
                first = False
            else:
                sys.argv[-1] = filepath
            main()

