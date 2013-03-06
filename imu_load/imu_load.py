import os.path

import numpy as np


class CameraParams(object):
    def __init__(self, fname):
        with open(fname, 'r') as f:
            lines = f.readlines()

        self.data = [self._process(l) for l in lines]

    @staticmethod
    def _process(info_line):
        print "processing %s" % info_line
        timestamp, phone, other_data = info_line.split("::")

        other_data_key_val = other_data.split(";")

        # stuff in other_data_key_val is of the format "key=value[,another_val]*"
        # so we need to split based on the equals then on the commas
        split_by_equals = [o.split("=") for o in other_data_key_val]
        full_key_vals = [(k, v.split(",")) for (k, v) in split_by_equals]

        ret_vals = dict(full_key_vals)

        return timestamp, phone, ret_vals


class Timestamped4Vec(object):
    def __init__(self, fname):
        with open(fname, 'r') as f:
            lines = f.readlines()

        split_lines = [l.split(",")[:-1] for l in lines]
        self.timestamps = np.array([int(ts[0]) for ts in split_lines], dtype=np.int64)

        self.data = np.array([[float(f) for f in ts[1:]] for ts in split_lines],
                             dtype=np.float64)


class TimestampedMtx(object):
    def __init__(self, fname):
        with open(fname, 'r') as f:
            lines = f.readlines()

        split_lines = [l.split(",") for l in lines]

        timestamps_int = [int(data[0]) for data in split_lines]

        # we have some mystery data first (ie there are 17 numbers when we definitely
        # want 16 for the matrix.
        self.mystery_data_ = [data[1] for data in split_lines]
        rot_matrices_str = [data[2:-1] for data in split_lines]

        # First elements of each line is time in nanoseconds
        self.timestamps = np.array(timestamps_int)

        # Build matrices then reshape to 4x4. FIXME: do we need to transform here?
        self.matrices = [np.array([float(r) for r in mtx]) for mtx in rot_matrices_str]
        self.matrices = [m.reshape(4, 4) for m in self.matrices]


class IMUSensorVideo(object):
    def __init__(self, vid_filename):
        self.vid_filename = vid_filename
        base_dir, vid_file_name = os.path.split(os.path.abspath(vid_filename))

        if not vid_file_name.lower().startswith("video-"):
            raise ValueError("expected filename to start with video-")
        if not vid_file_name.lower().endswith(".mp4"):
            raise ValueError("expected filename to end with mp4")

        # filename might be "video-17_Oct_2012_11-28-21_GMT.mp4" but the
        # title for everything we are looking for is:
        # 17_Oct_2012_11-28-21_GMT
        vid_id = vid_file_name[6:-4]

        print "vid_id =", vid_id

        metadata_dir_name = "videodata_video-" + vid_id

        print "metadata_dir_name =", metadata_dir_name

        abs_metadata_dir = os.path.join(base_dir, metadata_dir_name)

        # self._filenames_and_handlers must be defined in subclass!!
        for fname, python_name, handler in self._filenames_and_handlers:

            full_fname = os.path.join(abs_metadata_dir, fname + vid_id + ".txt")
            print "handling %s with %s" % (full_fname, handler)
            self.__dict__[python_name] = handler(full_fname)


class HTC1XVid(IMUSensorVideo):
    # This list defines what data files we should look for from an HTC 1X video,
    # what class we should wrap it with, then what we call it within the class
    _filenames_and_handlers = [
        ("AltOrientation_", "alt_orient", Timestamped4Vec),
        ("AltOrientationFromRotationVector_", "alt_orient_rot_vec", Timestamped4Vec),
        ("Panasonic_3-axis_Acceleration_sensor_", "pan_3_ax_acc", Timestamped4Vec),
        ("Panasonic_3-axis_Magnetic_Field_sensor_", "pan_3_ax_mag", Timestamped4Vec),
        ("Panasonic_Gravity_", "pan_grav", Timestamped4Vec),
        ("Panasonic_Gyroscope_sensor_", "pan_gyro", Timestamped4Vec),
        ("Panasonic_Linear_Acceleration_", "pan_acc", Timestamped4Vec),
        ("Panasonic_Orientation_sensor_", "pan_orient", Timestamped4Vec),
        ("Panasonic_Rotation_Vector_", "pan_rot_vec", Timestamped4Vec),
        ("RotationMatrix_", "rot", TimestampedMtx),
        ("RotationMatrixFromRotationVector_", "rot_from_vec", TimestampedMtx),
        ("CameraParams_", "camera_params", CameraParams),
    ]

    def __init__(self, vid_filename):
        super(HTC1XVid, self).__init__(vid_filename)

