#!/usr/bin/python

import sys
import subprocess
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import fnmatch

args = ArgumentParser(formatter_class = RawDescriptionHelpFormatter,
                          description = "CSV results parser and grapher")
args.add_argument('--csv_file',
                      help = "CSV file",
                          metavar = 'csv_file', type = str, default = None)
args.add_argument('--out_file',
                      help = "Output file format",
                          metavar = 'out_file', type = str, default = None)
args.add_argument('--avg_stats',
                      help = "Parse AVG total CSV files", action = 'store_true')
args.add_argument('--csv_dir',
                      help = "CSV dir to search recursively for files",
                          metavar = 'csv_dir', type = str, default = None)
largs = args.parse_args()
csv_files = []
infile = largs.csv_file
outfile  = largs.out_file
csvdir = largs.csv_dir
if not infile:
    print "Error: must specify --csv_file <filename/pattern>, add --csv_dir to search"
    sys.exit(1)
if ',' in infile:
    if not outfile:
        print "Error: must specify --out_file <filebase> for multiple CSV files"
        sys.exit(1)
    infiles = infile.split(',')
    for f in infiles:
        csv_files.append(f)
elif csvdir:
    if not outfile:
        print "Error: must specify --out_file <filebase> for multiple CSV files"
        sys.exit(1)
    for root, dirnames, filenames in os.walk(csvdir):
        for filename in fnmatch.filter(filenames, infile):
            csv_files.append(os.path.join(root,filename))
else:
    csv_files.append(infile)
    if not outfile:
        outfile = infile
avg_stats = largs.avg_stats


os.environ["GDFONTPATH"] = "/usr/share/fonts/msttcorefonts/"

# create gnuplot for msu scores
def get_gp(statsfile, of, label, labels, ymax):
    gp_file =  "set terminal png size 1920,1080 enhanced font \"arial,18\" \n\
set output '%s' \n\
\n\
set style line 2 lc rgb 'black' lt 1 lw 1\n\
set style data histogram \n\
set key opaque \n\
set style histogram cluster gap 1 \n\
set style fill pattern border -1 \n\
set boxwidth 0.9 \n\
set yrange [0:%d]\n\
set xtics format \"\" \n\
set xtics rotate \n\
set grid ytics \n\
\n\
set title \"%s\" \n\
plot \"%s\" using %d:xtic(1) title \"%s\" ls 2" % (of, ymax, label, statsfile, 2, labels[0])
    for idx, name in enumerate(labels[1:], start=2):
        #print "%d: %s" % (idx, name)
        gp_file += ", \"%s\" using %d title \"%s\" ls 2" % (statsfile, idx + 1, name)
    gp_file += "\n"
    return gp_file

# create gnuplot for bitrates
def get_gp_score(statsfiles, of, label, labels):
    gp_file =  "set terminal png size 1920,1080 enhanced font \"arial,18\" \n\
set output '%s' \n\
set key opaque \n\
set grid ytics \n\
set grid xtics \n\
set xtics rotate \n\
set yrange [0:5]\n\
set xrange [0:10000]\n\
\n\
set title \"%s\" \n\
plot \"%s\" using 1:2 title \"%s\" with points pointsize 3" % (of, label, statsfiles[0], labels[0])
    for idx, name in enumerate(labels[1:], start=1):
        gp_file += ", \"%s\" using 1:2 title \"%s\" with points pointsize 3" % (statsfiles[idx], name)
    gp_file += "\n"
    return gp_file

data = {}

label_avg = {}
label_br = {}
found_media = False
end_of_line = False

task_type = ""
one_to_each = 0
number_of_tests = 0
number_of_videos = 0
reference_video = 0

for csv_file in csv_files:
    print "CSVresult: %s" % csv_file
    f = open("%s" % csv_file)
    line = f.readline()
    csv_dir_path = os.path.dirname(csv_file)
    if csv_dir_path and csv_dir_path != "" and csv_dir_path[-1] != "/":
        csv_dir_path += "/"
    while line:
        line = line.strip("\n")
        if line.startswith("AVERAGE MARKS"):
            avg_stats = True
        if line.startswith("task type,"):
            task_type = line.split(',')[1].strip(' ')
        if line.startswith("one to each,"):
            one_to_each = int(line.split(',')[1].strip(' '))
        if line.startswith("number of tests,"):
            number_of_tests = int(line.split(',')[1].strip(' '))
        if line.startswith("number of videos,"):
            number_of_videos = int(line.split(',')[1].strip(' '))
        if line.startswith("reference video,"):
            reference_video = line.split(',')[1]
        if (line.startswith("C:") or line.startswith("RESULT: ")) and "Microsoft RLE," not in line:
            found_media = True
            scount = len(line.split(','))
            if avg_stats:
                a = line.split('\\')
                # bad line check
                if not a[-1]:
                    print "Error, line is not correct: %s" % line
                    continue 
                b = a[-1].strip(' ').split(',') 
                
                # split filename into parts
                c = b[0].split('.')[0].split('_')

                hash = c[1]
                start_time = c[2]
                end_time = c[3]
                label = c[4]
                avg = float(b[1])
                leftc = float(b[2])
                rightc = float(b[3])
                stddev = float(b[4])
                testname = "%s_%s_%s" % (hash, start_time, end_time)
                if testname not in data:
                    data[testname] = {}
                if label not in data[testname]:
                    data[testname][label] = {}
                if label not in label_avg:
                    label_avg[label] = []
                label_avg[label].append(avg)
                data[testname][label]["msu_avg"] = avg
                stats_file = "%sCLIP_%s_%s.stats" % (csv_dir_path, testname, label)
                if os.path.isfile(stats_file):
                    sf = open("%s" % stats_file)
                    bitrate = sf.readline().split(',')[3]
                    sf.close()
                    print "Found stats File: %s, bitrate:  %s" % (stats_file, bitrate)
                    data[testname][label]["bitrate"] = int(bitrate)
                    if label not in label_br:
                        label_br[label] = []
                    label_br[label].append(int(bitrate))
                else:
                    data[testname][label]["bitrate"] = 0
                    if label not in label_br:
                        label_br[label] = []
                    label_br[label].append(0)
            else:
                a = line.split(',')

                count = len(a) - 1
                offset = count / 2
                idx = 0

                while idx < offset:
                    #print "Result: %s: %s" % (a[idx], a[idx + offset])
                    v1c = a[idx].split('\\')[-1].split('.')[0].split('_')
                    hash1 = v1c[1]
                    s1 = float(a[idx + offset])
                    start_time1 = v1c[2]
                    end_time1 = v1c[3]
                    label1 = v1c[4]

                    if label1 not in label_avg:
                        label_avg[label1] = []
                    label_avg[label1].append(s1)

                    testname1 = "%s_%s_%s" % (hash1, start_time1, end_time1)
                    if testname1 not in data:
                        data[testname1] = {}
                    if label1 not in data[testname1]:
                        data[testname1][label1] = {}
                    data[testname1][label1]["msu_avg"] = s1
                    idx += 1
                    stats_file = "%sCLIP_%s_%s.stats" % (csv_dir_path, testname1, label1)
                    print "Looking for stats file: %s" % stats_file
                    if os.path.isfile(stats_file):
                        sf = open("%s" % stats_file)
                        bitrate = sf.readline().split(',')[3]
                        sf.close()
                        print "Found stats File: %s, bitrate:  %s" % (stats_file, bitrate)
                        data[testname1][label1]["bitrate"] = int(bitrate)
                        if label1 not in label_br:
                            label_br[label1] = []
                        label_br[label1].append(int(bitrate))
                    else:
                        data[testname1][label1]["bitrate"] = 0
                        if label not in label_br:
                            label_br[label] = []
                        label_br[label1].append(0)
        elif found_media:
            found_media = False
            
        line = f.readline()
    f.close()

print "%r" % data

labels_titles = []
label_list = []
task_results = []
br_results= []
br_msu_results = {}

for task in data:
    label_data = []
    br_data = []
    for label in sorted(data[task]):
        if label not in label_list:
            label_list.append(label)
            avg_total = 0.0
            br_total = 0.0
            br_average = 0.0
            for avg in label_avg[label]:
                avg_total += avg
            if label in label_br:
                for br in label_br[label]:
                    br_total += br
                br_average = br_total / float(len(label_br[label]))
            average = avg_total / float(len(label_avg[label]))
            labels_titles.append("%s msu: %0.2f bitrate: %0.2f Kbps" % (label, average, (br_average/1000.0)))
        label_data.append(str(data[task][label]["msu_avg"]))
        if "bitrate" in data[task][label]:
            br_data.append(str(data[task][label]["bitrate"]/1000))
            if label not in br_msu_results:
                br_msu_results[label] = []
            br_msu_results[label].append("%s\t%s" % (str(data[task][label]["bitrate"]/1000), str(data[task][label]["msu_avg"])))
    task_results.append("%s\t%s" % (task, '\t'.join(label_data)))
    br_results.append("%s\t%s" % (task, '\t'.join(br_data)))

source_stats = "%s.dat" % outfile
source_br_stats = "%s_br.dat" % outfile
output_jpg = "%s.jpg" % outfile
output_br_jpg = "%s_br.jpg" % outfile
gnuplotfile_gp = "%s.gp" % outfile
gnuplotfile_br_gp = "%s_br.gp" % outfile

label_string = '\t'.join(label_list)
label_title = ' | '.join(labels_titles)

# create msu_score:bitrate pairs per test encode type
br_dat_files = []
br_labels = []
for l in br_msu_results:
    source_br_msu_stats = "%s_%s.dat" % (outfile, l)
    br_dat_files.append(source_br_msu_stats)
    br_labels.append(l)
    with open(source_br_msu_stats, "w") as f:
        body = '\n'.join(br_msu_results[l])
        f.write("# %s\n%s\n" % ("bitrate\tscore", body))

if len(br_labels) <= 0:
    print "No CSV files found, exiting"
    sys.exit(0)

output_br_msu_jpg = "%s_brscore.jpg" % outfile
gnuplotfile_br_msu_gp = "%s_brscore.gp" % outfile
with open(gnuplotfile_br_msu_gp, "w") as f:
    body = get_gp_score(br_dat_files, "%s" % output_br_msu_jpg, "Bitrate vs. Score", br_labels)
    f.write("%s\n" % body)

task_results.sort()
with open(source_stats, "w") as f:
    body = '\n'.join(task_results)
    f.write("# task\t%s\n%s\n" % (label_string, body))

br_results.sort()
with open(source_br_stats, "w") as f:
    body = '\n'.join(br_results)
    f.write("# task\t%s\n%s\n" % (label_string, body))

ymax = 5
if avg_stats:
    ymax = 10
with open(gnuplotfile_gp, "w") as f:
    body = get_gp("%s" % source_stats, "%s" % output_jpg, label_title, label_list, ymax)
    f.write("%s\n" % body)

with open(gnuplotfile_br_gp, "w") as f:
    body = get_gp("%s" % source_br_stats, "%s" % output_br_jpg, label_title, label_list, 10000)
    f.write("%s\n" % body)

subprocess.call(['gnuplot', '--persist', "%s" % gnuplotfile_gp])
subprocess.call(['gnuplot', '--persist', "%s" % gnuplotfile_br_gp])
subprocess.call(['gnuplot', '--persist', "%s" % gnuplotfile_br_msu_gp])

