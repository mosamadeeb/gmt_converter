import argparse
import os
import io

from structure.version import GAME, GMT_VERSION, GMTProperties
from converter import convert, combine, reset_camera, vector_org, Translation


def main():
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

    parser = argparse.ArgumentParser(description=description, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-ig', '--ingame', action='store', help='source game')
    parser.add_argument('-og', '--outgame', action='store', help='target game')
    parser.add_argument('-i', '--inpath', action='store', help='GMT input name (or input folder path)')
    parser.add_argument('-o', '--outpath', action='store', help='GMT output name')
    parser.add_argument('-mtn', '--motion', action='store_true', help='output GMT will be used in \'motion\' folder (for post-Y5)')
    parser.add_argument('-rst', '--reset', action='store_true', help='reset body position to origin point at the start of the animation')
    parser.add_argument('-rhct', '--resethact', action='store_true', help='reset whole hact scene to position of the input gmt (requires both -i as a single file and -d) [overrides --reset]')
    parser.add_argument('-aoff', '--addoffset', action='store', help='additional height offset for resetting hact scene (for pre-DE hacts) [will be added to scene height]')

    parser.add_argument('-rp', '--reparent', action='store_true', help='reparent bones for this gmt between models')
    parser.add_argument('-fc', '--face', action='store_true', help='translate face bones for this gmt between models')
    parser.add_argument('-hn', '--hand', action='store_true', help='translate hand bones for this gmt between models')
    parser.add_argument('-bd', '--body', action='store_true', help='translate body (without face or hand) bones for this gmt between models')
    parser.add_argument('-sgmd', '--sourcegmd', action='store', help='source GMD for translation')
    parser.add_argument('-tgmd', '--targetgmd', action='store', help='target GMD for translation')

    parser.add_argument('-d', '--dir', action='store_true', help='the input is a dir')
    parser.add_argument('-dr', '--recursive', action='store_true', help='the input is a dir; recursively convert subfolders')
    parser.add_argument('-ns', '--nosuffix', action='store_true', help='do not add suffixes at the end of converted files')
    parser.add_argument('-sf', '--safe', action='store_true', help='ask before overwriting files')
    
    parser.add_argument('-cmb', '--combine', action='store_true', help='combine split animations inside a directory (for pre-Y5 hacts) [WILL NOT CONVERT]')
    
    # TODO: add drag and drop support: interactive cli inputs to get required info
    args = parser.parse_args()
    
    translation = Translation(args.reparent, args.face, args.hand, args.body, args.sourcegmd, args.targetgmd, args.reset, args.resethact, args.addoffset)
    
    if not args.inpath:
        if os.path.isdir("input_folder"):
            args.dir = True
            args.inpath = "\"input_folder\""
        else:
            print("usage: gmt_converter.exe [-h] [-ig INGAME] [-og OUTGAME] [-i INPATH] [-o OUTPATH] [-mtn] [-rst] [-rhct] [-rp] [-fc] [-hn] [-bd] \
                                          [-sgmd SOURCEGMD] [-tgmd TARGETGMD] [-d] [-dr] [-ns] [-sf] [-cmb]\n")
            print("Error: Provide an input path with -i or put the files in \"<gmt_converter_path>\\input_folder\\\"")
            os.system('pause')
            return
    
    if args.combine:
        collect(args.inpath, args.outpath, args.nosuffix)
        return
    
    if not args.ingame:
        args.ingame = input("Enter source game:\n")
    if not args.outgame:
        args.outgame = input("Enter target game:\n")
    
    args.ingame = args.ingame.lower()
    args.outgame = args.outgame.lower()
    
    if args.dir or args.recursive:
        args.dir = True
        if not args.outpath:
            args.outpath = "output_folder"
        if args.inpath.lower() == args.outpath.lower() and args.nosuffix:
            print("Error: Input path cannot be the same as output path when using --nosuffix with -d or -dr")
            os.system('pause')
            return
    else:
        if not args.outpath:
            if args.nosuffix:
                print("Error: Provide an output path when using --nosuffix without -d or -dr")
                os.system('pause')
                return
            args.outpath = args.inpath[:-4] + f"-{args.outgame}.gmt"
        if args.inpath.lower() == args.outpath.lower():
            print("Error: Input path cannot be the same as output path when not using -d or -dr")
            os.system('pause')
            return
    
    if args.ingame not in GAME:
        print(f"Error: Game \'{args.ingame}\' is not supported")
        os.system('pause')
        return
    if args.outgame not in GAME:
        print(f"Error: Game \'{args.outgame}\' is not supported")
        os.system('pause')
        return
    if not translation.has_operation() and not translation.has_reset():
        if args.ingame == args.outgame:
            print(f"Error: Cannot convert to the same game")
            os.system('pause')
            return
        if GMT_VERSION[GAME[args.ingame]] == GMT_VERSION[GAME[args.outgame]]:
            print(f"Error: Conversion is not needed between \'{args.ingame}\' and \'{args.outgame}\'")
            os.system('pause')
            return

    if args.motion is None:
        args.motion = False
        if GMTProperties(GAME[args.outgame]).new_bones and not GMTProperties(GAME[args.ingame]).new_bones:
            print(f"Is the target GMT for {args.outgame} a motion GMT?")
            if input("(y/n) ").lower() == 'y':
                args.motion = True
    
    if translation.resethact:
        # TODO: also reset cmts
        translation.reset = False
        translation.offset = vector_org(args.inpath)
        args.inpath = os.path.dirname(args.inpath)
    
    if args.dir:
        for r, d, f in os.walk(args.inpath):
            for file in f:
                gmt_file = os.path.join(r, file)
                #if not gmt_file.startswith('\"'):
                #    gmt_file = f"\"{gmt_file}\""
                if args.nosuffix:
                    output_file = os.path.join(args.outpath, file)
                else:
                    output_file = os.path.join(args.outpath, file[:-4] + f"-{args.outgame}.gmt")
                
                stop = False
                for g in GAME.keys():
                    if g in gmt_file[-9:-4]:
                        stop = True
                        break
                if stop:
                    continue
                
                if translation.resethact:
                    if gmt_file.endswith('.cmt'):
                        output_file = output_file[:-4] + '.cmt'
                        is_de = GMTProperties(GAME[args.ingame]).is_dragon_engine
                        with open(output_file, 'wb') as g:
                            g.write(reset_camera(gmt_file, translation.offset, translation.add_offset, is_de))
                            print(f"converted {output_file}")
                        continue
                
                if not gmt_file.endswith('.gmt'):
                    continue
                
                if args.safe and os.path.isfile(output_file):
                    print(f"Output file \"{output_file}\" already exists. Overwrite? (select 's' to stop conversion)")
                    result = input("(y/n/s) ").lower()
                    if result != 'y':
                        if result == 's':
                            print("Stopping operation...")
                            os.system('pause')
                            return
                        print(f"Skipping \"{output_file}\"...")
                        continue
                with open(output_file, 'wb') as g:
                    g.write(convert(gmt_file, args.ingame, args.outgame, args.motion, translation))
                    print(f"converted {output_file}")
            if not args.recursive:
                break
    else:
        if args.safe and os.path.isfile(args.outpath):
            print(f"Output file \"{args.outpath}\" already exists. Overwrite?")
            result = input("(y/n) ").lower()
            if result != 'y':
                print("Stopping operation...")
                os.system('pause')
                return
        #if not args.inpath.startswith('\"'):
        #    args.inpath = f"\"{args.inpath}\""
        with open(args.outpath, 'wb') as g:
            g.write(convert(args.inpath, args.ingame, args.outgame, args.motion, translation))
            print(f"converted {args.outpath}")
    print("DONE")

def collect(path, outpath, nosuffix):
    def file_index(name):
        return int(name[-7:-4])
    
    if not outpath:
        outpath = os.path.join("output_folder", os.path.basename(path))
    if not os.path.isdir(outpath):
        os.mkdir(outpath)
    
    suf = '-combined'
    if nosuffix:
        suf = ''
    
    gmts = []
    cmts = []
    for r, d, f in os.walk(path):
        for file in f:
            anm_file = os.path.join(r, file)
            if anm_file.endswith('.gmt'):
                gmts.append(anm_file)
            elif anm_file.endswith('.cmt'):
                cmts.append(anm_file)

    for gmt in gmts:
        if gmt[-7:-4] == '000':
            common = os.path.basename(gmt)[:-7]
            gmt_path = f"{os.path.join(outpath, common[:-1])}{suf}"
            files = [name for name in gmts if common in name]
            i = 0
            for f in combine(sorted(files, key=file_index), 'gmt'):
                with open(f"{gmt_path}_{i}.gmt", 'wb') as gmt:
                    gmt.write(f[0])
                print(f"combined {f[1]} files into {gmt_path}_{i}.gmt")
                i += 1
    
    for cmt in cmts:
        if cmt[-7:-4] == '000':
            common = os.path.basename(cmt)[:-7]
            cmt_path = f"{os.path.join(outpath, common[:-1])}{suf}"
            files = [name for name in cmts if common in name]
            i = 0
            for f in combine(sorted(files, key=file_index), 'cmt'):
                with open(f"{cmt_path}_{i}.cmt", 'wb') as cmt:
                    cmt.write(f[0])
                print(f"combined {f[1]} files into {cmt_path}_{i}.cmt")
                i += 1
    
    print("DONE")
    os.system('pause')

if __name__ == "__main__":
    main()