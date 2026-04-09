import argparse

from .util.db_path_config import write_tools_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tools-path", required=True)
    args = p.parse_args()
    
    write_tools_path(args.tools_path)
    
if __name__ == '__main__':
    main()
