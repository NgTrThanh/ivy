import cv2
import sys
import os
from VehicleCounter import VehicleCounter
import numpy as np
import uuid
import contextlib
import argparse


# parse CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument('video', help='relative/absolute path to video or camera input of traffic scene')
parser.add_argument('--iscam', action='store_true', help='specify if video capture is from a camera')
parser.add_argument('--droi', help='specify a detection region of interest (ROI) \
                    i.e a set of vertices that represent the area (polygon) \
                    where you want detections to be made (format: 1,2|3,4|5,6|7,8|9,10 \
                    default: 0,0|frame_width,0|frame_width,frame_height|0,frame_height \
                    [i.e the whole video frame])')
parser.add_argument('--showdroi', action='store_true', help='display/overlay the detection roi on the video')
parser.add_argument('--mcdf', type=int, help='maximum consecutive detection failures \
                    i.e number of detection failures before it\'s concluded that \
                    an object is no longer in the frame')
parser.add_argument('--mctf', type=int, help='maximum consecutive tracking failures \
                    i.e number of tracking failures before the tracker concludes \
                    the tracked object has left the frame')
parser.add_argument('--di', type=int, help='detection interval i.e number of frames \
                    before detection is carried out again (in order to find new vehicles \
                    and update the trackers of old ones)')
parser.add_argument('--detector', help='select a model/algorithm to use for vehicle detection \
                    (options: yolo, haarc, bgsub, ssd, tfoda | default: yolo)')
parser.add_argument('--tracker', help='select a model/algorithm to use for vehicle tracking \
                    (options: csrt, kcf, camshift | default: kcf)')
parser.add_argument('--record', action='store_true', help='record video and vehicle count logs')
parser.add_argument('--headless', action='store_true', help='run VCS without UI display')
parser.add_argument('--clposition', help='position of counting line (options: top, bottom, \
                    left, right | default: bottom)')
args = parser.parse_args()

# capture traffic scene video
video = int(args.video) if args.iscam else args.video
cap = cv2.VideoCapture(video)
if not cap.isOpened():
    sys.exit('Error capturing video.')
ret, frame = cap.read()
f_height, f_width, _ = frame.shape

di = 10 if args.di == None else args.di
mcdf = 2 if args.mcdf == None else args.mcdf
mctf = 3 if args.mctf == None else args.mctf
detector = 'yolo' if args.detector == None else args.detector
tracker = 'kcf' if args.tracker == None else args.tracker
# create detection region of interest polygon
if args.droi == None:
    droi = [(0, 0), (f_width, 0), (f_width, f_height), (0, f_height)]
else:
    tmp_droi = []
    points = args.droi.replace(' ', '').split('|')
    for point_str in points:
        point = tuple(map(int, point_str.split(',')))
        tmp_droi.append(point)
    droi = tmp_droi

vehicle_counter = VehicleCounter(frame, detector, tracker, droi, args.showdroi, mcdf, mctf, di, args.clposition)

if args.record:
    # initialize video object and log file to record counting
    output_video_path='./videos/output.avi'
    output_video = cv2.VideoWriter(output_video_path, \
                                        cv2.VideoWriter_fourcc('M','J','P','G'), \
                                        30, \
                                        (f_width, f_height))
    log_file_name='log.txt'
    with contextlib.suppress(FileNotFoundError):
        os.remove(log_file_name)
    log_file = open(log_file_name, 'a')
    log_file.write('vehicle_id, count, datetime\n')
    log_file.flush()

# main loop
print('VCS running...')
while args.iscam or cap.get(cv2.CAP_PROP_POS_FRAMES) + 1 < cap.get(cv2.CAP_PROP_FRAME_COUNT):
    if ret:
        log = vehicle_counter.count(frame)
        output_frame = vehicle_counter.visualize()

        if args.record:
            output_video.write(output_frame)
            for item in log:
                _row = '{0}, {1}, {2}\n'.format('v_' + str(item['blob_id']), item['count'], item['datetime'])
                log_file.write(_row)
                log_file.flush()

        if not args.headless:
            resized_frame = cv2.resize(output_frame, (858, 480))
            cv2.imshow('tracking', resized_frame)

    k = cv2.waitKey(1) & 0xFF
    # save frame if 's' key is pressed
    if k == ord('s'):
        cv2.imwrite(os.path.join('screenshots', 'ss_' + uuid.uuid4().hex + '.png'), output_frame)
        print('Screenshot taken.')
    # end video loop if 'q' key is pressed
    if k == ord('q'):
        print('Video exited.')
        break
    
    ret, frame = cap.read()

# end capture, close window, close log file and video object if any
cap.release()
if not args.headless:
    cv2.destroyAllWindows()
if args.record:
    log_file.close()
    output_video.release()
print('Processing ended.')