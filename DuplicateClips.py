from PIL import Image
import imagehash
import cv2
import hashlib
from datetime import datetime


def get_curr_time():
    # print(datetime.now())
    return datetime.now()


class DuplicateClips:

    def __init__(self, video_path):
        self.curr_video = cv2.VideoCapture(video_path)
        self.frames_per_second = self.get_number_of_frames_per_second_in_video()
        self.matching_frames = []
        self.total_frames = 0
        self.frame_diff_count_for_next_clip = 60
        self.immediate_match_frame_diff_max_count = 15
        self.seconds_per_minute = 60
        self.find_frames_hash()

    def get_number_of_frames_per_second_in_video(self):
        # Find OpenCV version
        (major_ver, minor_ver, subminor_ver) = cv2.__version__.split('.')

        if int(major_ver) < 3:
            fps = self.curr_video.get(cv2.cv.CV_CAP_PROP_FPS)
            # print("Frames per second using video.get(cv2.cv.CV_CAP_PROP_FPS): {0}".format(fps))
        else:
            fps = self.curr_video.get(cv2.CAP_PROP_FPS)
            # print("Frames per second using video.get(cv2.CAP_PROP_FPS) : {0}".format(fps))
        return int(fps)

    def find_frames_hash(self):
        """
        matching frames by frame hash
        dict[frame_hash] = [frame_count_no, 3, 4]
        getting & returning the matched frames in list
        [1,2,3, 21,22,23]
        [6,7,8, 41,42,46]
        ..
        """
        frame_count = 0

        frames_dict = {}
        success = 1
        while success:
            # vidObj object calls read
            # function extract frames
            success, image = self.curr_video.read()
            if not success:
                break
            # print(type(image))
            image = Image.fromarray(image)
            frame_hash = imagehash.dhash(image)
            # frame_hash = hashlib.md5(image.tobytes())
            if frame_hash in frames_dict:
                frames_dict[frame_hash].append(frame_count)
            else:
                frames_dict[frame_hash] = [frame_count]

            frame_count += 1
        self.total_frames = frame_count

        # getting all matched frame sequences
        self.matching_frames = []
        for key, val in frames_dict.items():
            # print(val)
            self.matching_frames.append(val)
        # sorting the matching frames
        self.matching_frames.sort(key=lambda x: x[0])

    def convert_matched_frames_to_clip_list(self):
        """
        finding the clips in the matched frames list & separating frames by their difference number
        [1,2,3, 21,22,23] to [[1,2,3],[21,22,23]] as [[1,3],[21,23]]
        [6,7,8, 41,42,46] to [[6,7,8],[41,42,46]] as [[6,8],[41,46]]
        :return: matched frame clips list
        """
        matched_frame_clips_list = []
        for frame_combo in self.matching_frames:
            new_combo = []
            new_frames = []
            # reading frame combo
            is_frame_match_found = False
            for i in range(0, len(frame_combo) - 1):
                curr_ele = frame_combo[i]
                next_ele = frame_combo[i + 1]
                new_frames.append(curr_ele)
                if (next_ele - curr_ele) >= self.frame_diff_count_for_next_clip:
                    is_frame_match_found = True
                    first_last_frames = [new_frames[0], new_frames[-1]]
                    new_combo.append(first_last_frames)
                    new_frames = []
                if i == len(frame_combo) - 2:
                    new_frames.append(next_ele)
                    first_last_frames = [new_frames[0], new_frames[-1]]
                    new_combo.append(first_last_frames)
            if is_frame_match_found:
                matched_frame_clips_list.append(new_combo)
        return matched_frame_clips_list

    def merge_immediate_matching_frames(self, matched_frame_clips_list):
        """
        merging the matched clips list, if the next frame number is close to current one
        [[1,3],[21,23]
        [4,6],[25,27]]
        to
        [[1,6],[21,27]]
        :param matched_frame_clips_list: matched frame clips list
        :return: merged frame clips list
        """
        if len(matched_frame_clips_list) < 2:
            print("No Matches")
            exit(0)
        base_frames = matched_frame_clips_list[0]
        merged_frame_clips_list = []
        i = 1
        while i < len(matched_frame_clips_list):
            curr_frames = matched_frame_clips_list[i]
            j = 0
            while j < len(curr_frames) and j < len(base_frames):
                base_frame = base_frames[j]
                curr_frame = curr_frames[j]
                next_frame_diff = curr_frame[0] - base_frame[1]
                if 0 < next_frame_diff < self.immediate_match_frame_diff_max_count:
                    base_frames[j][1] = curr_frame[1]
                if next_frame_diff > self.immediate_match_frame_diff_max_count:
                    merged_frame_clips_list.append(base_frames)
                    base_frames = curr_frames
                    break
                j += 1
            i += 1
        merged_frame_clips_list.append(base_frames)
        return merged_frame_clips_list

    def convert_merged_frames_to_minutes_format(self, merged_frame_clips_list):
        """
        converting the merged frames to minutes format
        [[1,50],[158,201]] to [['0.0', '0.2],[6.08, 8.01]]
        :param merged_frame_clips_list: merged frame clips list
        :return:
        """
        duplicate_clips_list = []
        for frame_combos in merged_frame_clips_list:
            frames_in_sec = []
            for frame_combo in frame_combos:
                start_sec = round((frame_combo[0] / self.frames_per_second))
                end_sec = round((frame_combo[1] / self.frames_per_second))
                start_sec = str(start_sec // self.seconds_per_minute) + "." + str(start_sec % self.seconds_per_minute)
                end_sec = str(end_sec // self.seconds_per_minute) + "." + str(end_sec % self.seconds_per_minute)
                if start_sec == end_sec:
                    continue
                frames_in_sec.append([start_sec, end_sec])
            if len(frames_in_sec) > 1:
                duplicate_clips_list.append(frames_in_sec)
        return duplicate_clips_list

    def get_duplicate_clips_info(self):
        print("\nProcessing Frames Started: {0}".format(get_curr_time()))
        matched_frame_clips_list = self.convert_matched_frames_to_clip_list()
        merged_frame_clips_list = self.merge_immediate_matching_frames(matched_frame_clips_list)
        duplicate_clips_list = self.convert_merged_frames_to_minutes_format(merged_frame_clips_list)
        print("Processing Frames Completed: {0}".format(get_curr_time()))
        print("\nDuplicate Clips:")
        for clip in duplicate_clips_list:
            print(clip)

    def print_vid_details(self):
        print("\nVideo Details:")
        print("Frames per second: {0}".format(self.frames_per_second))
        print("Total Frames count : {0}".format(self.total_frames))
        print("Total Frames count video.get(cv2.CAP_PROP_FRAME_COUNT) : {0}".
              format(self.curr_video.get(cv2.CAP_PROP_FRAME_COUNT)))

    def close(self):
        self.curr_video.release()
        cv2.destroyAllWindows()

    def __del__(self):
        self.close()


if __name__ == '__main__':
    # video_to_check = "/home/rajesh/Downloads/temp/jab_pandu.mp4"
    video_to_check = "/home/rajesh/Downloads/temp/sample-mp4-file_1.mp4"
    # video_to_check = "/home/rajesh/Downloads/temp/vid_test/videoplayback.mp4"
    print("Hashing Process Started: {0}".format(get_curr_time()))
    duplicate_clip = DuplicateClips(video_to_check)
    print("Hashing Process Completed: {0}".format(get_curr_time()))
    duplicate_clip.print_vid_details()
    duplicate_clip.get_duplicate_clips_info()
