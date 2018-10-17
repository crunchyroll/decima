#!/usr/bin/python

# Create Task (Subjective video quality evaluation)
# - read a json file referencing a mezzanine reference video
#   with clip in/out points and encode variations for each
#   clip in/out points comparison against the mezzanine.
#
# Requires: Tkinter, ffmpeg, mediainfo
#   mpv

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import datetime
import fnmatch
import json
import os
import random
from shutil import copyfile
import subprocess
import sys
import time
from Tkinter import *

def secs2time(s):
    ms = int((s - int(s)) * 1000000)
    s = int(s)
    # Get rid of this line if s will never exceed 86400
    while s >= 24*60*60: s -= 24*60*60
    h = s / (60*60)
    s -= h*60*60
    m = s / 60
    s -= m*60
    timecode_microseconds = datetime.time(h, m, s, ms).isoformat()
    if '.' in timecode_microseconds:
        base_time, microseconds  = timecode_microseconds.split('.')
    else:
        base_time = timecode_microseconds
        microseconds = 0
    return "%s,%03d" % (base_time, int(microseconds) / 1000)

# Play video using mpv
def play_video(video, title):
    message = ['--osd-playing-msg', '%s' % title]
    cmd = "mediainfo --Inform=\"Video;%DisplayAspectRatio%,%FrameRate%,%Width%,%Height%\""
    vinfo = subprocess.check_output("%s %s" % (cmd, video), stderr=subprocess.STDOUT, shell=True).split(',')
    width = int(vinfo[2])
    height = int(vinfo[3])
    sar = "1/1"
    rate = vinfo[1]
    subprocess.call(['mpv', video, '--osd-playing-msg', title, '--osc=no', '--osd-bar=no', '--fs', '--opengl-glfinish=yes', '--opengl-early-flush=no', '--lavfi-complex=color=c=Black:duration=1:size=%dx%d:rate=%s:sar=%s[black];color=c=Gray:duration=1:size=%dx%d:rate=%s:sar=%s[gray];color=c=Gray:duration=1:size=%dx%d:rate=%s:sar=%s[gray2];[vid1]setsar=sar=%s[video];[black][gray][video][gray2]concat=n=4:unsafe=1[vo]' % (width, height, rate, sar, width, height, rate, sar, width, height, rate, sar, sar)]) 

# Play blended video using mpv
def play_video_overlay(mezzanine, encode, blend_mode, mezz_level, enc_level, mode, width, height, fps, srt_file):
    if mode == "blend":
        subprocess.call(['mpv', '--fs', '--opengl-glfinish=yes', '--opengl-early-flush=no', '--osd-bar=no', '--osc=no',
            mezzanine, '--external-file', encode,
            '--lavfi-complex=[vid1]fps=%s,scale=%s:%s,format=yuva420p,colorchannelmixer=aa=%s,setpts=PTS-STARTPTS[mezzanine];[vid2]fps=%s,scale=%s:%s,format=yuva420p,colorchannelmixer=aa=%s,setpts=PTS-STARTPTS[encode];[mezzanine][encode]blend=%s[vo]' % (fps, width, height, mezz_level, fps, width, height, enc_level, blend_mode)]) 
    elif mode == "difference":
        subprocess.call(['mpv', '--fs', '--opengl-glfinish=yes', '--opengl-early-flush=no', '--osd-bar=no', '--osc=no',
            mezzanine, '--external-file', encode, '--external-file', encode,
            '--lavfi-complex=[vid1]fps=%s,scale=%s:%s,format=yuva444p,lut=c3=128,negate,setpts=PTS-STARTPTS[mezzanine];[vid2]fps=%s,scale=%s:%s,setpts=PTS-STARTPTS[encode];[encode][mezzanine]overlay[vo]' % (fps, width, height, fps, width, height), '--sub-file=%s' % srt_file]) 
    elif mode == "pip":
        subprocess.call(['mpv', '--fs', '--opengl-glfinish=yes', '--opengl-early-flush=no', '--osd-bar=no', '--osc=no',
            mezzanine, '--external-file', encode, '--external-file', encode,
            '--lavfi-complex=[vid1]fps=%s,scale=%s:%s,format=yuva444p,lut=c3=128,negate,setpts=PTS-STARTPTS[mezzanine];[vid2]fps=%s,scale=%s:%s,setpts=PTS-STARTPTS[encode];[encode][mezzanine]overlay[differences];[vid3]fps=%s,scale=in_w/4:in_h/4,format=yuva444p,lut=c3=220,setpts=PTS-STARTPTS[pip];[differences][pip]overlay=(W-w)/2:(H-h)/2[vo]' % (fps, width, height, fps, width, height, fps), '--sub-file=%s' % srt_file]) 
    elif mode == "sidebyside":
        cmd = "mediainfo --Inform=\"Video;%DisplayAspectRatio%,%FrameRate%,%Width%,%Height%\""
        vinfo = subprocess.check_output("%s %s" % (cmd, mezzanine), stderr=subprocess.STDOUT, shell=True).split(',')
        width = int(vinfo[2])
        height = int(vinfo[3])
        sar = "%s/%s" % (width, height)
        rate = vinfo[1]
        subprocess.call(['mpv', '--fs', '--opengl-glfinish=yes', '--opengl-early-flush=no', '--osd-bar=no', '--osc=no',
            mezzanine, '--external-file', encode,
            '--lavfi-complex=color=c=Black:duration=1:size=%dx%d:rate=%s:sar=%s[black];color=c=Gray:duration=1:size=%dx%d:rate=%s:sar=%s[gray];color=c=Gray:duration=1:size=%dx%d:rate=%s:sar=%s[gray2];[vid1]fps=%s,scale=%s/2:%s,setsar=sar=%s,setpts=PTS-STARTPTS[mezzanine];[vid2]fps=%s,scale=%s/2:%s,setsar=sar=%s,setpts=PTS-STARTPTS[encode];[mezzanine][encode]hstack[sbs];[black][gray][sbs][gray2]concat=n=4:unsafe=1[vo]' % (width, height, rate, sar, width, height, rate, sar, width, height, rate, sar, fps, width, height, sar, fps, width, height, sar)]) 

# Play video using Bino
def play_video_bino(mezzanine, encode, mode):
    subprocess.call(['/Applications/Bino.app/Contents/MacOS/Bino', '-n', '-f', '-o', mode, mezzanine, encode]) 

def get_user():
    username = "unknown"
    master = Tk()
    def ignore(event):
        master.quit()
        return "break"
    master.title("Decima: Human Visual Quality Assessment System")
    master.bind("<Return>", ignore)
    l = Label(master, justify=CENTER, text="\n\nEnter your name:", font=("Helvetica", 36))
    l.pack(side=TOP)
    e = Entry(master, justify=CENTER, width=25)
    e.focus_set()
    e.focus_force()
    e.pack(side=TOP)
    l2 = Label(master, justify=CENTER, text="(first initial and last name format)", font=("Helvetica", 16))
    l2.pack(side=TOP)
    l1 = Label(master, justify=CENTER, text="Press <Return> to continue", font=("Helvetica", 18))
    l1.pack(side=TOP)
    instructions = """
            Tests launch automatically upon login, you will proceed through each test using the spacebar
            to play each reference then the variant encoding.  After viewing the reference and variant encode,
            you will rate the encode quality in comparison to the reference video.
            The space bar is used to play each test, the backspace key is used to repeat tests or skip tests.
            The arrow keys work for the 1-5 score slider bar at the end of each test.

            Please logout after finished with all the tests.  If leaving early then use the
            Command+Q key sequence to exit the testing software. The system should time out a login after a 
            15 minute time period of no activity, so if you leave it may log you out (preferable to logout when leaving).
            You can easily come back to continue testing (it will ask if you want to retake tests you have already taken.
            """

    l3 = Label(master, justify=LEFT, text=instructions, font=("Helvetica", 14))
    l3.pack(side=TOP)
    master.update_idletasks()
    master.attributes("-alpha", True)
    master.attributes("-fullscreen", True)
    master.attributes("-topmost", True)
    master.attributes("-notify", True)
    master.focus_set()
    master.focus_force()
    master.lift()
    os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

    master.mainloop()
    username = e.get()
    master.destroy()
    return username

# confirmation, backspace replay, return continue
def check_replay(message, bmessage):
    master = Tk()
    def replay_video(event):
        master.quit()
        return "break"
    def stop(event):
        master.destroy()
        return "break"
    master.title("Decima: Human Visual Quality Assessment System")
    master.bind("<Return>", stop)
    master.bind("<space>", stop)
    master.bind("<BackSpace>", replay_video)
    w = Label(master, takefocus=True, justify=CENTER, text="\n%s" % message, font=("Helvetica", 36))
    w.pack(side=TOP)
    w1 = Label(master, takefocus=True, justify=CENTER, text="\n%s" % bmessage, font=("Helvetica", 18))
    w1.pack(side=TOP)
    # bring window to front and center
    master.update_idletasks()
    master.attributes("-alpha", True)
    master.attributes("-fullscreen", True)
    master.attributes("-topmost", True)
    master.attributes("-notify", True)
    master.lift()
    master.focus_set()
    master.focus_force()
    if sidebyside:
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    master.mainloop()
    try:
        master.destroy()
    except:
        print "Stopping video playback"
        return False
    print "Replaying video"
    return True

# Print message and wait for user input
def ask_user(message, bmessage):
    master = Tk()
    def ignore(event):
        master.destroy()
        return "break"
    def bino(event):
        global sidebyside
        global overlay
        global bino
        sidebyside = True
        overlay = False
        bino = True
        print "Switching to bino mode"
        master.destroy()
        return "break"
    def sbs(event):
        global sidebyside
        global overlay
        sidebyside = True
        overlay = False
        print "Switching to side by side mode"
        master.destroy()
        return "break"
    def normal(event):
        global sidebyside
        global overlay
        sidebyside = False
        overlay = False
        print "Switching to normal mode"
        master.destroy()
        return "break"
    def overlay(event):
        global sidebyside
        global overlay
        global overlaymode
        sidebyside = False
        overlay = True
        overlaymode = "blend"
        print "Switching to overlay mode"
        master.destroy()
        return "break"
    def difference(event):
        global sidebyside
        global overlay
        global overlaymode
        sidebyside = False
        overlay = True
        overlaymode = "difference"
        print "Switching to difference mode"
        master.destroy()
        return "break"
    def pip(event):
        global sidebyside
        global overlay
        global overlaymode
        sidebyside = False
        overlay = True
        overlaymode = "pip"
        print "Switching to pip mode"
        master.destroy()
        return "break"
    master.title("Decima: Human Visual Quality Assessment System")
    master.bind("<F1>", sbs)
    master.bind("<F2>", overlay)
    master.bind("<F3>", normal)
    master.bind("<F4>", difference)
    master.bind("<F5>", pip)
    master.bind("<F6>", bino)
    master.bind("<Return>", ignore)
    master.bind("<space>", ignore)
    w = Label(master, takefocus=True, justify=CENTER, text="\n%s" % message, font=("Helvetica", 36))
    w.pack(side=TOP)
    w2 = Label(master, takefocus=True, justify=CENTER, text="press <SpaceBar> to start test\n\n To switch viewing mode:\n F1: side-by-side\n F2: overlay\n F3: DSIS\n F4: difference\n F5: pip\n F6: bino", font=("Helvetica", 18))
    w2.pack(side=TOP)
    # bring window to front and center
    master.update_idletasks()
    master.attributes("-topmost", True)
    master.attributes("-alpha", True)
    master.attributes("-notify", True)
    master.attributes("-fullscreen", True)
    master.focus_set()
    master.focus_force()
    master.lift()
    if sidebyside:
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    master.mainloop()

# Get ITU Style video quality score
def score_video(video, idx, title):
    master = Tk()
    skip = False
    def skipscore(event):
        global skip
        skip = True
        master.quit()
        return "break"
    def repeat(event):
        master.destroy()
        return "break"
    def submit(event):
        master.quit()
        return "break"
    def up(event):
        if w1.get() < 5:
            w1.set(w1.get()+1)
        return "break"
    def down(event):
        if w1.get() > 0:
            w1.set(w1.get()-1)
        return "break"
    master.title("Decima: Human Visual Quality Assessment System")
    master.bind("<Return>", submit)
    # setup window slider bar and information on each value
    w = Label(master, takefocus=True, justify=CENTER, text="%s Test #%02d\nEncoding impairments are?" % (title, idx), font=("Helvetica", 36))
    w.pack(side=TOP)
    w3 = Label(master, takefocus=True, justify=LEFT,
            text="5: Imperceptible\n4: Perceptible, but not annoying\n3: Slightly annoying\n2: Annoying\n1: Very annoying",
            font=("Helvetica", 25))
    w3.pack(side=TOP)
    w1 = Scale(master, from_=1, to=5, tickinterval=1, length=300, orient=HORIZONTAL, font=("Helvetica", 18))
    master.bind("<Left>", down)
    master.bind("<Right>", up)
    master.bind("<BackSpace>", repeat)
    master.bind("<Escape>", skipscore)
    w1.set(5)
    w1.pack(side=TOP)
    # submit button
    Button(master, justify=CENTER, text='Submit', command=master.quit, font=("Helvetica", 18)).pack(side=TOP)
    w4 = Label(master, takefocus=True, justify=CENTER, text="Use the Left/Right arrow keys to score then press <Return> to record or <BackSpace> to repeat test or <Escape> to skip scoring this test", font=("Helvetica", 18))
    w4.pack(side=TOP)
    # bring window to front and center
    master.update_idletasks()
    master.attributes("-topmost", True)
    master.attributes("-alpha", True)
    master.attributes("-notify", True)
    master.attributes("-fullscreen", True)
    master.focus_set()
    master.focus_force()
    master.lift()
    if sidebyside:
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    master.mainloop()

    # skip scoring if requested
    if skip:
        return -1

    # return score or repeat test
    try:
        score = w1.get()
        master.destroy()
    except:
        # user chose to not save results
        return 0

    return score

# input takes a dict of tests to run through
#  test_cwd, title, test_index, mezzanine_clip, encode_clip, score_file
def run_tests(tests):
    global username
    while not username:
        username = get_user()
    test_scores = {}
    original_cwd = os.getcwd()
    tests_items=tests.items() # List of tuples
    random.shuffle(tests_items)
    for testkey, test in tests_items:
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)
        title = test["title"]
        test_index = test["test_index"]
        mezzanine_clip = test["mezzanine_clip"]
        mezz_width = test["mezz_width"]
        mezz_height = test["mezz_height"]
        encode_clip = test["encode_clip"]
        score_file = "%s_%s.csv" % (test["score_file"], username)
        label = test["label"]
        score_file_tmp = "%s_%s_%s.tmp" % (test["score_file"], username, label)
        test_cwd = test["test_cwd"]
        total_tests = test["total_tests"]
        srt_file = test["psnr_srt"]
        encode_stats = test["encode_stats"].split(',')
        fps = encode_stats[2]
        width = encode_stats[5]
        height = encode_stats[6]
        os.chdir(test_cwd)

        dotest = True
        if not overlay and os.path.exists(score_file) and os.path.getsize(score_file) > 0:
            if check_replay("%s Test #%02d\nRetake previous assessment?" % (title, test_index), "Press <SpaceBar> to retake this test again\n\nPress <BackSpace> to keep previous scores and skip this test"):
                dotest = False
            else:
                # delete stale tmp files
                if os.path.exists(score_file_tmp):
                    os.remove(score_file_tmp)
                # remove score file
                if os.path.exists(score_file):
                    os.remove(score_file)

        test_replay = 0
        while dotest:
            # check if test was already done
            score = 0
            if not overlay and os.path.exists(score_file_tmp) and os.path.getsize(score_file_tmp) > 0:
                # open file, get score
                with open(score_file_tmp, 'r') as f:
                    score = int(f.read())
            else:
                test_replay += 1
                if bino:
                    ask_user("%s Test #%02d\nPlay the original source mezzanine and an encode with Bino." % (title, test_index), "Play videos with Bino")
                    # user changed modes
                    if not sidebyside:
                        continue
                    play_video_bino(mezzanine_clip, encode_clip, sidebysidemode)
                elif sidebyside:
                    ask_user("%s Test #%02d\nPlay the original source mezzanine and an encode." % (title, test_index), "Play videos side by side")
                    # user changed modes
                    if not sidebyside:
                        continue
                    play_video_overlay(mezzanine_clip, encode_clip, blendmode, mezz_alpha, enc_alpha, "sidebyside", width, height, fps, srt_file)
                elif overlay:
                    ask_user("%s Test #%02d\nPlay the original source mezzanine with encode overlay %s." % (title, test_index, overlaymode), "Play videos with overlay")
                    # user changed modes
                    if not overlay:
                        continue
                    play_video_overlay(mezzanine_clip, encode_clip, blendmode, mezz_alpha, enc_alpha, overlaymode, width, height, fps, srt_file)
                else:
                    ask_user("%s Test #%02d\nPlay the original source mezzanine." % (title, test_index), "Play reference video")
                    if overlay or sidebyside:
                        continue
                    while True:
                        play_video(mezzanine_clip, "Reference")
                        if not check_replay("%s Test #%02d\nPlay encode?" % (title, test_index), "Press <SpaceBar> to play encode\n\nPress <BackSpace> to replay reference"):
                            break
                    play_video(encode_clip, "Encode")
                score = -1
                if not overlay:
                    score = score_video(mezzanine_clip, test_index, title) 

            if score == -1:
                break
            elif score != 0:
                print "%s score %d" % (encode_clip, score)
                if score_file not in test_scores:
                    test_scores[score_file] = {}
                    test_scores[score_file]["scores"] = {}
                    test_scores[score_file]["tmp_files"] = []
                test_scores[score_file]["scores"][encode_clip] = int(score)
                test_scores[score_file]["test_cwd"] = test_cwd
                test_scores[score_file]["score_file"] = score_file
                test_scores[score_file]["title"] = title
                test_scores[score_file]["test_index"] = test_index
                test_scores[score_file]["tmp_files"].append(score_file_tmp)
                test_scores[score_file]["total_tests"] = total_tests
                test_scores[score_file]["mezz_height"] = mezz_height
                test_scores[score_file]["mezz_width"] = mezz_width

                # write tmp scorefile
                with open(score_file_tmp, "w") as f:
                    f.write("%d\n" % int(score))

                break

        # parse test scores
        for score_file, test_score in dict.iteritems(test_scores):
            if os.getcwd() != original_cwd:
                os.chdir(original_cwd)
            # create score file in the ITU format
            mezz_h = int(test_score["mezz_height"])
            mezz_w = int(test_score["mezz_width"])
            scores = test_score["scores"]
            title = test_score["title"]
            test_index = test_score["test_index"]
            test_cwd = test_score["test_cwd"]
            total_tests = test_score["total_tests"]

            os.chdir(test_cwd)

            if len(scores) >= total_tests:
                with open(score_file, "w") as f:
                    f.write("number of tests, %d\n" % len(scores))
                    f.write("number of videos, %d\n" % (len(scores)+1))
                    f.write("reference video, C:\\videos\%s\n" % mezzanine_clip)
                    f.write("video, mark\n")
                    for test in scores:
                        f.write("C:\\videos\%s,%d,\n" % (test, scores[test]))
                    f.write("\nScreen resolution, width, %d, height, %d,\n" % (mezz_w, mezz_h))
                    f.write("\ntime of assessment, %s,\n" % datetime.date.today().strftime('%H:%M %d/%m/%Y'))

                # delete tmp score files
                for tmp_file in test_score["tmp_files"]:
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
            else:
                print "%d of %d tests for %s completed" % (len(scores), total_tests, mezzanine_clip)

    os.chdir(original_cwd)
    check_replay("Finished with tests, please logoff of the system", "Press <SpaceBar> to exit")
    return test_scores


args = ArgumentParser(formatter_class = RawDescriptionHelpFormatter,
                          description = "Creates Subjective Video Quality tests")
args.add_argument('--hash_id',
                      help = "Hash ID",
                          metavar = 'hash_id', type = str, default = None)
args.add_argument('--username',
                      help = "Username of tester",
                          metavar = 'username', type = str, default = None)
args.add_argument('--tasks_file',
                      help = "Tasks file",
                          metavar = 'tasks_file', type = str, default = None)
args.add_argument('--mezzanine_file',
                      help = "Mezzanine to use",
                          metavar = 'mezzanine_file', type = str, default = None)
args.add_argument('--output_dir',
                      help = "Output directory path for encodes",
                          metavar = 'output_dir', type = str, default = None)
args.add_argument('--debug',
                      help = "Debug", action = 'store_true')
args.add_argument('--dryrun',
                      help = "Dryrun", action = 'store_true')
args.add_argument('--runtests',
                      help = "Runtests", action = 'store_true')
args.add_argument('--showresults',
                      help = "show result graphs", action = 'store_true')
args.add_argument('--rawyuv',
                      help = "Create raw YUV video too", action = 'store_true')
args.add_argument('--sidebyside',
                      help = "Show video side by side", action = 'store_true')
args.add_argument('--sidebysidemode',
                      help = "mode to use for Bino output display using -o",
                          metavar = 'sidebysidemode', type = str, default = "left-right")
args.add_argument('--bino',
                      help = "Play with Bino", action = 'store_true')
args.add_argument('--overlay',
                      help = "Show mezzanine with encode overlay video", action = 'store_true')
args.add_argument('--blendmode',
                      help = "Blend mode to use for libav blend filter",
                          metavar = 'blendmode', type = str, default = "overlay")
args.add_argument('--overlaymode',
                      help = "Overlay mode to use for libav overlay mode (blend or difference)",
                          metavar = 'overlaymode', type = str, default = "blend")
args.add_argument('--mezz_alpha',
                      help = "Alpha channel transparency level of mezzanine (0.9 by default)",
                          metavar = 'mezz_alpha', type = str, default = "0.9")
args.add_argument('--enc_alpha',
                      help = "Alpha channel transparency level of encode 0.6 by default)",
                          metavar = 'enc_alpha', type = str, default = "0.6")
args.add_argument('--creategraphs',
                      help = "create graphs after tests are ran", action = 'store_true')
args.add_argument('--ffmpeg_options',
                      help = "extra options for ffmpeg",
                          metavar = 'ffmpeg_options', type = str, default = None)

largs = args.parse_args()
tasks_file_input = largs.tasks_file
mezzanine_file = largs.mezzanine_file
output_dir = largs.output_dir
hash_id = largs.hash_id
debug = largs.debug
dryrun = largs.dryrun
runtests = largs.runtests
rawyuv = largs.rawyuv
username = largs.username
showresults = largs.showresults
sidebyside = largs.sidebyside
bino = largs.bino
overlay = largs.overlay
blendmode = largs.blendmode
overlaymode = largs.overlaymode
sidebysidemode = largs.sidebysidemode
mezz_alpha = largs.mezz_alpha
enc_alpha = largs.enc_alpha
creategraphs = largs.creategraphs
ffmpeg_options = largs.ffmpeg_options

if output_dir and not os.path.exists(output_dir): 
    print "Error, must specify a valid output directory for --output_dir <dir>"
    sys.exit(1)
else:
    if output_dir and output_dir[-1] != "/":
        output_dir += "/"
    else:
        output_dir = ""

tasks_files = []
if tasks_file_input and tasks_file_input.split(',') > 0:
    tasks_files = tasks_file_input.split(',')
else:
    tasks_files.append(tasks_file_input)

# collect tests to run
tests_to_run = {}

original_cwd = os.getcwd()
for tasks_file in tasks_files:
    # change back to base dir we started in per task file
    if os.getcwd() != original_cwd:
        os.chdir(original_cwd)

    # skip non-existing task files
    if not tasks_file or not os.path.exists(tasks_file):
        print "Error, must specify a valid json tasks file for --tasks_file <file> %s" % tasks_file
        continue

    # check if task file is within another directory
    tasks_file_dir = os.path.dirname(tasks_file)
    tasks_file = os.path.basename(tasks_file)

    # chdir into tasksfile dir if it isn't in our current dir
    if tasks_file_dir != "":
        os.chdir(tasks_file_dir)

    with open(tasks_file, 'r') as f:
        tasks = json.load(f)

    if debug:
        print "%r" % tasks

    # Mezzanine setup
    mezzanine = mezzanine_file
    if "mezzanine" in tasks:
        if not mezzanine and tasks["mezzanine"]:
            mezzanine = tasks["mezzanine"]

    # get hash id
    if "id" in tasks:
        hash_id = tasks["id"]
    else:
        hash_id = "0"

    print "Using mezzanine[%s]: %s" % (hash_id, mezzanine)

    # get list of test encodes
    tests = None
    if "tests" in tasks:
        tests = tasks["tests"]
    else:
        print "No tests found to create encodes for!"
        sys.exit(1)

    # get list of clips
    clips = None
    if "clips" in tasks:
        clips = tasks["clips"]
    else:
        print "No clips found to create encodes for!"
        sys.exit(1)

    # walk through clips and show tests for each clip
    for clip in clips:
        if "start" in clip and "duration" in clip:
            start = clip["start"]
            duration = clip["duration"]
            if not runtests and rawyuv:
                mezzanine_ext = "avi"
            else:
                mezzanine_ext = mezzanine.split('.')[-1]
            if mezzanine_ext == "y4m":
                mezzanine_ext = "yuv"
            mezzanine_clip = "%sCLIP_%s_%s_%s_%s.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), "mezz", mezzanine_ext)
            print "Range Start: %s Duration: %s Output: %s" % (start, duration, mezzanine_clip)
            # create mezzanine time range clip in YUV
            if not os.path.exists(mezzanine_clip) or os.path.getsize(mezzanine_clip) < 256:
                if not runtests and rawyuv:
                    cmd = "ffmpeg -hide_banner -y -nostdin -i \"%s\" -vcodec rawvideo -pix_fmt yuv420p -dn -sn -an -ss \"%s\" -t \"%s\" \"%s\"" % (mezzanine, start, duration, mezzanine_clip)
                else:
                    cmd = "ffmpeg -hide_banner -y -nostdin -i \"%s\" -vcodec copy -dn -sn -an -ss \"%s\" -t \"%s\" \"%s\"" % (mezzanine, start, duration, mezzanine_clip)
                print "Running: %s" % cmd
                if not dryrun:
                    os.system(cmd)
            else:
                print "Mezzanine already exists: %s" % mezzanine_clip

            # create thumbnails per scene change
            image_base = "%sCLIP_%s_%s_%s_images" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'))
            if not os.path.isdir(image_base):
                os.mkdir(image_base)
                cmd = "ffmpeg -hide_banner -i \"%s\" -r 1 -an \"%s/%%03d.jpg\"" % (mezzanine_clip, image_base)
                os.system(cmd)

            # create tiled mosaic of scene change images
            if not os.path.isfile("%s.jpg" % image_base):
                cmd = "ffmpeg -hide_banner -i \"%s\" -vf fps=1,scale=160:120,tile -frames:v 1 -vsync 0 -an \"%s.jpg\"" % (mezzanine_clip, image_base)
                os.system(cmd)

            # show images
            if showresults:
                cmd = "mpv --osd-playing-msg \"Push 'q' to continue.\" --loop --fs %s.jpg" % image_base
                os.system(cmd)

            # playback mezzanine, video then score it
            title = "%s\nseason: %s\nepisode: %s\nstart_time: %s\nduration: %s\n\n" % (tasks["title"], tasks["season"], tasks["episode"], start, duration)

            # score file
            csv_files = []
            score_file = "RESULTS_%s_%s_%s" % (hash_id, start.replace(':', '-'), duration.replace(':', '-'))

            # setup each variant encoding with values specified
            test_scores = {}
            tests_items=tests.items() # List of tuples
            random.shuffle(tests_items)
            test_index = 0
            total_tests = len(tests)
            for test, settings in tests_items:
                test_index += 1
                ext = "mp4"
                if settings["codec"] == "vp9":
                    ext = "webm"
                encode_clip = "%sCLIP_%s_%s_%s_%s.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), test, ext)
                decode_clip = "%sCLIP_%s_%s_%s_%s.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), test, "avi")
                decode_clip_stats = "%sCLIP_%s_%s_%s_%s.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), test, "stats")
                mezzanine_clip_stats = "%sCLIP_%s_%s_%s.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), "stats")
                encode_clip_psnr_metrics = "%sCLIP_%s_%s_%s_%s_psnr.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), test, "metrics")
                encode_clip_psnr_srt = "%sCLIP_%s_%s_%s_%s_psnr.%s" % (output_dir, hash_id, start.replace(':', '-'), duration.replace(':', '-'), test, "srt")
                print "  Test %s %s:" % (test, encode_clip)

                # get mezzanine stats
                if not os.path.exists(mezzanine_clip_stats) or os.path.getsize(mezzanine_clip_stats) <= 0:
                    # create stats file
                    cmd = "mediainfo --Inform=\"Video;%ID%,%DisplayAspectRatio%,%FrameRate%,%BitRate%,%CodecID%,%Width%,%Height%,%Encoded_Library_Settings%\""
                    print "Running stats for: %s" % mezzanine_clip
                    vinfo = subprocess.check_output("%s %s" % (cmd, mezzanine_clip), stderr=subprocess.STDOUT, shell=True).strip('\n')
                    with open(mezzanine_clip_stats, "w") as f:
                        f.write("%s" % vinfo)

                # get mezzanine stats
                mezzanine_stats = ""
                mezz_fps = "30"
                mezz_height = "1080"
                mezz_width = "1920"
                if os.path.exists(mezzanine_clip_stats) and os.path.getsize(mezzanine_clip_stats) > 0:
                    with open(mezzanine_clip_stats, "r") as f:
                        mezzanine_stats = f.read()
                    mezz_fps = mezzanine_stats.split(',')[2]
                    mezz_width = mezzanine_stats.split(',')[5]
                    mezz_height = mezzanine_stats.split(',')[6]
                else:
                    print "Warning: missing mezz stats file - %s" % mezzanine_clip_stats

                # create encoding variant with env vars set
                if not os.path.exists(encode_clip) or os.path.getsize(encode_clip) < 256:
                    _environ = os.environ.copy()
                    for key, value in dict.iteritems(settings): 
                        os.environ[key] = value
                        if debug:
                            print "    %s: %s" % (key, value)
                    os.environ["fps"] = mezz_fps
                    if ffmpeg_options:
                        os.environ["extra_options"] = ffmpeg_options
                    cmd = "encode %s %s %s" % (mezzanine_clip, encode_clip, os.environ["codec"])
                    print "Running: %s" % cmd
                    if not dryrun:
                        os.system(cmd)
                    os.environ.clear()
                    os.environ.update(_environ)
                else:
                    print "Encode already exists: %s" % encode_clip

                # encode stats
                if not os.path.exists(decode_clip_stats) or os.path.getsize(decode_clip_stats) <= 0:
                    # create stats file
                    cmd = "mediainfo --Inform=\"Video;%ID%,%DisplayAspectRatio%,%FrameRate%,%BitRate%,%CodecID%,%Width%,%Height%,%Encoded_Library_Settings%\""
                    print "Running stats for: %s" % encode_clip
                    vinfo = subprocess.check_output("%s %s" % (cmd, encode_clip), stderr=subprocess.STDOUT, shell=True).strip('\n')
                    with open(decode_clip_stats, "w") as f:
                        f.write("%s" % vinfo)

                # get encode clip metrics
                if not os.path.exists(encode_clip_psnr_metrics) or os.path.getsize(encode_clip_psnr_metrics) < 0:
                    mezz_res = "%s:%s" % (mezz_width, mezz_height)
                    print "Creating SSIM and PSNR stats for %s" % encode_clip 
                    cmd = "ffmpeg -hide_banner -y -nostdin -i %s -i %s -lavfi \"[0:v]scale=%s[a];[1:v]scale=%s[b];[a][b]psnr=%s\" -f null -" % (encode_clip, mezzanine_clip, mezz_res, mezz_res, encode_clip_psnr_metrics)
                    print "%s" % cmd
                    os.system(cmd)

                # transform encode clip metrics into an srt file
                if not os.path.exists(encode_clip_psnr_srt) or os.path.getsize(encode_clip_psnr_srt) < 0:
                    print "Creating PSNR srt for %s" % encode_clip 
                    psnr_metrics = None
                    with open(encode_clip_psnr_metrics, "r") as f:
                        psnr_metrics = f.readlines()
                    psnr_metrics = [x.strip() for x in psnr_metrics]
                    with open(encode_clip_psnr_srt, "w") as f:
                        for l in psnr_metrics:
                            parts = l.split(' ')
                            frame = parts[0].split(':')[1]
                            psnr_avg = parts[5].split(':')[1]
                            start_seconds = (1.0/float(mezz_fps)) * float(frame)
                            end_seconds = (1.0/float(mezz_fps)) * (float(frame) + .9)
                            start_time = secs2time(start_seconds)
                            end_time = secs2time(end_seconds)
                            srt_line = "%s\n%s --> %s\nTIMECODE[%s] PSNR[%s]\n\n" % (frame, start_time, end_time, start_time, psnr_avg)
                            f.write(srt_line)

                # video stats for encode
                encode_stats = ""
                if os.path.exists(decode_clip_stats) and os.path.getsize(decode_clip_stats) > 0:
                    with open(decode_clip_stats, "r") as f:
                        encode_stats = f.read()

                # create YUV decoded version and .avs AviSynth file wrapper
                if not os.path.exists(decode_clip) or os.path.getsize(decode_clip) < 256:
                    cmd = "decode %s %s" % (encode_clip, decode_clip)
                    if not runtests and rawyuv:
                        print "Running: %s" % cmd
                        if not dryrun:
                            os.system(cmd)
                else:
                    print "Decode already exists: %s" % decode_clip

                test_key = "%s_%s" % (score_file, test)
                if test_key not in tests_to_run:
                    tests_to_run[test_key] = {}
                tests_to_run[test_key]["test_cwd"] = os.getcwd()
                tests_to_run[test_key]["title"] = title
                tests_to_run[test_key]["test_index"] = test_index 
                tests_to_run[test_key]["mezzanine_clip"] = mezzanine_clip
                tests_to_run[test_key]["encode_clip"] = encode_clip 
                tests_to_run[test_key]["score_file"] = score_file 
                tests_to_run[test_key]["label"] = test
                tests_to_run[test_key]["total_tests"] = total_tests
                tests_to_run[test_key]["encode_stats"] = encode_stats
                tests_to_run[test_key]["mezz_fps"] = mezz_fps
                tests_to_run[test_key]["mezz_height"] = mezz_height
                tests_to_run[test_key]["mezz_width"] = mezz_width
                tests_to_run[test_key]["psnr_srt"] = encode_clip_psnr_srt

            # analyze results and create graphs if they exist
            # /mob/www/results/0001/task_vp9/*_03rjreh9870rray_00-02-45_00-00-15*/*.csv
            if creategraphs:
                dir_search_path = "RESULTS_%s_%s_%s_" % (hash_id, start.replace(':', '-'), duration.replace(':', '-'))
                print "Searching for %s" % dir_search_path
                for root, dirs, files in os.walk('.'):
                    for filename in files:
                        if filename.endswith(('.csv')):
                            if filename.startswith((dir_search_path)):
                                print "Found results file: %s" % filename
                                csv_files.append(filename)

                for csv_file in csv_files:
                    fbase = os.path.basename(csv_file)
                    directory = os.path.dirname(csv_file)
                    cmd = "parse_results.py --csv_file \"%s\"" % fbase
                    os.system(cmd)
                    # show results
                    if showresults:
                        cmd = "mpv --osd-playing-msg \"Push 'q' to continue.\" -loop --fs %s.jpg" % fbase
                        os.system(cmd)
                        cmd = "mpv --osd-playing-msg \"Push 'q' to continue.\" --loop --fs %s_br.jpg" % fbase
                        os.system(cmd)
                        cmd = "mpv --osd-playing-msg \"Push 'q' to continue.\" -loop --fs %s_brscore.jpg" % fbase
                        os.system(cmd)


if runtests:
    run_tests(tests_to_run)

