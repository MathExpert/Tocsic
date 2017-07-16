#!/usr/bin/env python3

import re
import os
import argparse


class Tocsic:
    toc_marker = '# Table of Contents'

    head_regex = re.compile(r'(#+)\s*(\S+(?:\s+\S+)*)')
    keyword_regex = re.compile(r'\s*<!-- ?keyword:\s*(\w+).*')

    def __init__(self):
        self.args = None

        self.input_file = None
        self.output_file = None
        self.is_overwrite = False

        self.make_arguments()
        self.check_arguments()

        self.toc_info = []
        self.toc = Tocsic.toc_marker + '\n'
        self.body = ''

        try:
            self.file = open(self.input_file, 'r')
        except IOError:
            raise TocsicException('Failed to open file ' + self.input_file)

        self.is_valid = True

    def make_arguments(self):
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument('filename', type=str, help='path to Markdown document')
        arg_parser.add_argument('-c', '--clean', help='remove table of contents if present')
        arg_parser.add_argument('-o', '--output', type=str, help='output file', default=None)
        # TODO: add an option for handling empty header names
        # TODO: add an option for handling other keyword formats
        # TODO: add an option for disabling keyword processing
        self.args = arg_parser.parse_args()

    def check_arguments(self):
        md_path = self.args.filename
        if not os.path.exists(md_path) or not os.path.isfile(md_path):
            raise TocsicException('{} does not exist or is not a file'.format(md_path))

        self.input_file = md_path

        if self.args.output is not None:
            self.output_file = self.args.output
            if self.output_file == self.input_file:
                self.is_overwrite = True
                if not is_user_sure('Output file is the same as input file, rewrite? [y/n]'):
                    self.is_valid = False
                    return
        else:
            self.output_file = self.make_output_name(self.input_file)

    @staticmethod
    def make_output_name(filename):
        if '.' not in filename:
            return filename + '_toc'

        return '.cot_'.join(filename[::-1].split('.', 1))[::-1]

    def add_toc(self):
        if not self.is_valid:
            return

        line_gen = FileReader(self.file)
        if self.process_start(line_gen):
            self.process_toc(line_gen)
        self.process_body(line_gen)
        self.file.close()
        # TODO: add toc error-checking and maybe some postprocessing

        self.make_toc()
        self.generate_md()

    @staticmethod
    def process_start(line_gen):
        try:
            line = next(line_gen).strip()
            while not line:
                line = next(line_gen).strip()

            line_gen.back()
            if line == Tocsic.toc_marker:
                return True
            else:
                return False
        except StopIteration:
            pass

    @staticmethod
    def process_toc(line_gen):
        try:
            line = next(line_gen).strip()
            while line:
                print(line)
                line = next(line_gen).strip()

            line_gen.back()
        except StopIteration:
            pass

    def process_body(self, line_gen):
        line = ''

        try:
            while True:
                line, prev_line = next(line_gen), line
                self.body += line
                # TODO: make sure we are not in a block of code
                # TODO: add support for === and --- style headers
                if line.startswith('#'):
                    self.make_toc_entry(line, line_gen.line_num, prev_line)
                    pass
        except StopIteration:
            pass

    def make_toc_entry(self, line, line_num, keyword_line=None):
        search_res = re.search(Tocsic.head_regex, line)
        if not search_res:
            raise TocsicException('Line {} starts with "#" but is not a header'.format(line_num))

        header = search_res.groups()
        level = len(header[0]) - 1
        # TODO: generate correct header name if header contains characters that don't work in links
        header_name = header[1]
        link = header_name.lower().replace(' ', '-')

        if keyword_line:
            search_res = re.search(Tocsic.keyword_regex, keyword_line)
            if search_res:
                link = search_res.groups()[0]

        self.toc_info.append((level, header_name, link))

    def make_toc(self):
        for toc_entry in self.toc_info:
            self.toc += '{}1. [{}](#{})\n'.format('    ' * toc_entry[0], toc_entry[1], toc_entry[2])

    def generate_md(self):
        with open(self.output_file, 'w') as f:
            f.write(self.toc)
            f.write('\n')
            f.write(self.body)


class TocsicException(Exception):
    pass


class FileReader:
    def __init__(self, f):
        self.repeat = False
        self.last_line = None
        self.iter = iter(f)
        self.line_num = 0

    def __iter__(self):
        return self

    def back(self):
        self.repeat = True

    def __next__(self):
        if self.repeat:
            self.repeat = False
            return self.last_line
        else:
            self.last_line = next(self.iter)
            self.line_num += 1
            return self.last_line


def is_user_sure(message):
    print(message)
    while True:
        answer = input()
        if answer.lower() in ('y', 'yes'):
            return True
        elif answer.lower() in ('n', 'no'):
            return False
        else:
            print('Please type "y" or "n"')


if __name__ == '__main__':
    md = Tocsic()
    md.add_toc()
