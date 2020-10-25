import argparse
import os
import io
from typing import List, Union, Tuple

import requests

from .structure.version import GAME, GMT_VERSION, GMTProperties
from .converter import convert, combine, reset_camera, vector_org, Translation

description = """
A tool to convert animations between Yakuza games
Currently supported Games:
  - Yakuza 0:            y0
  - Yakuza Kiwami:       yk1
  - Yakuza Kiwami 2:     yk2
  - Yakuza 3:            y3
  - Yakuza 4:            y4
  - Yakuza 5:            y5
  - Yakuza 6:            y6
  - Yakuza Kenzan:       yken
  - Yakuza Ishin:        yish
  - Yakuza Dead Souls:   yds
  - FOTNS Lost Paradise: fotns
  - Judgment:            je

Note1: Conversion might not properly work for some specific combinations
Note2: All Dragon Engine games are the same, so y6 = yk2 = je

"""

epilog = """
EXAMPLE
Convert animations from Yakuza 5 to Yakuza 0
(source file is from Y5, target file will be used in Y0):

    gmt_converter.exe -ig y5 -og y0 -i animation_from_y5.gmt -o converted_y0_animation.gmt
    
If you want to convert an entire folder of GMTs, add the -d flag (or -dr to convert files in subfolders too):

    gmt_converter.exe -ig y0 -og y5 -d -i folder_containing_gmts

"""

parser = argparse.ArgumentParser(
    description=description, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-ig', '--ingame', action='store', help='source game')
parser.add_argument('-og', '--outgame', action='store', help='target game')
parser.add_argument('-i', '--inpath', action='store',
                    help='GMT input name (or input folder path)')
parser.add_argument('-o', '--outpath', action='store', help='GMT output name')
parser.add_argument('-mtn', '--motion', action='store_true',
                    help='output GMT will be used in \'motion\' folder (for post-Y5)')
parser.add_argument('-rst', '--reset', action='store_true',
                    help='reset body position to origin point at the start of the animation')
parser.add_argument('-rhct', '--resethact', action='store_true',
                    help='reset whole hact scene to position of the input gmt (requires both -i as a single file and -d) [overrides --reset]')
parser.add_argument('-aoff', '--addoffset', action='store',
                    help='additional height offset for resetting hact scene (for pre-DE hacts) [will be added to scene height]')

parser.add_argument('-rp', '--reparent', action='store_true',
                    help='reparent bones for this gmt between models')
parser.add_argument('-fc', '--face', action='store_true',
                    help='translate face bones for this gmt between models')
parser.add_argument('-hn', '--hand', action='store_true',
                    help='translate hand bones for this gmt between models')
parser.add_argument('-bd', '--body', action='store_true',
                    help='translate body (without face or hand) bones for this gmt between models')
parser.add_argument('-sgmd', '--sourcegmd', action='store',
                    help='source GMD for translation')
parser.add_argument('-tgmd', '--targetgmd', action='store',
                    help='target GMD for translation')

parser.add_argument('-d', '--dir', action='store_true',
                    help='the input is a dir')
parser.add_argument('-dr', '--recursive', action='store_true',
                    help='the input is a dir; recursively convert subfolders')
parser.add_argument('-ns', '--nosuffix', action='store_true',
                    help='do not add suffixes at the end of converted files')
parser.add_argument('-sf', '--safe', action='store_true',
                    help='ask before overwriting files')

parser.add_argument('-cmb', '--combine', action='store_true',
                    help='combine split animations inside a directory (for pre-Y5 hacts) [WILL NOT CONVERT]')


def process_args(args):
    translation = Translation(args.reparent, args.face, args.hand, args.body,
                              args.sourcegmd, args.targetgmd, args.reset, args.resethact, args.addoffset)

    if not args.ingame:
        # This should not happen as the bot should ask for this before accessing the converter
        print("Error: Source game not provided.")
        return -1
    if not args.outgame:
        # This should not happen as the bot should ask for this before accessing the converter
        print("Error: Target game not provided.")
        return -1

    args.ingame = args.ingame.lower()
    args.outgame = args.outgame.lower()

    if args.ingame not in GAME:
        print(f"Error: Game \'{args.ingame}\' is not supported")
        return -1
    if args.outgame not in GAME:
        print(f"Error: Game \'{args.outgame}\' is not supported")
        return -1

    if args.combine:
        return (args, translation)

    if not translation.has_operation() and not translation.has_reset():
        if args.ingame == args.outgame:
            print(f"Error: Cannot convert to the same game")
            return -1
        if GMT_VERSION[GAME[args.ingame]] == GMT_VERSION[GAME[args.outgame]]:
            print(
                f"Error: Conversion is not needed between \'{args.ingame}\' and \'{args.outgame}\'")
            return -1

    return (args, translation)


def collect(files, ingame, nosuffix):
    if GMTProperties(GAME[ingame]).version > GMTProperties('YAKUZA_5').version:
        start_index = -7  # TODO: change these correctly
        end_index = -4
    else:
        start_index = -7
        end_index = -4

    def file_index(name):
        return int(get_basename(gmt)[start_index:end_index])

    suf = '' if nosuffix else '-combined'

    gmts = []
    cmts = []
    combined = []

    for f in files:
        if get_basename(f).endswith('.gmt'):
            gmts.append(f)
        elif get_basename(f).endswith('.cmt'):
            cmts.append(f)

    for gmt in gmts:
        if get_basename(gmt)[start_index:end_index] == '000':
            common = get_basename(gmt)[:start_index]
            gmt_path = f"{common[:-1]}{suf}"
            files = []
            common_files = [f for f in gmts if common in get_basename(f)]
            for f in sorted(common_files, key=file_index):
                files.append(get_data(f))
            i = 0
            for f in combine(files, 'gmt'):
                combined.append((f"{gmt_path}_{i}.gmt", f[0]))
                print(f"combined {f[1]} files into {gmt_path}_{i}.gmt")
                i += 1

    for cmt in cmts:
        if cmt[start_index:end_index] == '000':
            common = os.path.basename(cmt)[:start_index]
            cmt_path = f"{common[:-1]}{suf}"
            files = []
            common_files = [f for f in cmts if common in get_basename(f)]
            for f in sorted(common_files, key=file_index):
                files.append(get_data(f))
            i = 0
            for f in combine(files, 'cmt'):
                combined.append((f"{cmt_path}_{i}.cmt", f[0]))
                print(f"combined {f[1]} files into {cmt_path}_{i}.cmt")
                i += 1

    return combined


def get_data(gmt: Union[str, Tuple[str, bytes]]):
    if type(gmt) is str:
        return gmt
    if type(gmt) is tuple:
        return gmt[1]


def get_basename(gmt: Union[str, Tuple[str, bytes]]):
    if type(gmt) is str:
        return os.path.basename(gmt)
    if type(gmt) is tuple:
        return gmt[0]


def convert_from_url_bytes(argv: List[str], gmt: Union[str, Tuple[str, bytes]]):
    processed = process_args(parser.parse_args(argv))
    if type(processed) is int:
        return processed
    args, translation = processed

    if type(gmt) is list:
        converted = []

        # Setup Hact resetting first
        if translation.resethact:
            translation.reset = False
            main_gmt = [m for m in gmt if get_basename(m) == args.inpath]
            if len(main_gmt):
                translation.offset = vector_org(main_gmt[0])
                new_gmt = []
                for g in gmt:
                    if get_basename(g).endswith('.gmt'):
                        new_gmt.append(g)
                    elif get_basename(g).endswith('.cmt'):
                        outpath = get_basename(g) if args.nosuffix else get_basename(g)[
                            :-4] + f"-{args.outgame}.cmt"
                        converted.append((outpath, reset_camera(
                            g, translation.offset, translation.add_offset, GMTProperties(GAME[args.ingame]).is_dragon_engine)))
                    gmt = new_gmt
            else:
                translation.reset = True
                translation.resethact = False

        if args.combine:
            return collect(gmt, args.ingame, args.nosuffix)
        for url in gmt:
            outpath = get_basename(url) if args.nosuffix else get_basename(url)[
                :-4] + f"-{args.outgame}.gmt"
            converted.append((outpath, convert(
                get_data(url), args.ingame, args.outgame, args.motion, translation)))

        return converted
    outpath = get_basename(url) if args.nosuffix else get_basename(url)[
        :-4] + f"-{args.outgame}.gmt"
    return((outpath, convert(get_data(gmt), args.ingame, args.outgame, args.motion, translation)))


if __name__ == "__main__":
    pass
