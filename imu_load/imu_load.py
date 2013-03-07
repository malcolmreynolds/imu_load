import os.path

import numpy as np


class TimestampedData(object):
    def total_time(self):
        """Returns the elapsed time in nanoseconds. This only makes
        sense when we have a reading"""
        return self.timestamps[-1] - self.timestamps[0]

    def __len__(self):
        return self.num_readings()

    def num_readings(self):
        return self.timestamps.size

    def reading_at_time(self, time_in_ns):
        """Given some NS time, return the measurement at a given time in
        nanoseconds. doesn't perform interpolation, so if we don't have a
        reading from that time, nothing will work."""

        # Find indices to all the entries of self.timestamps
        # which match the given time (there SHOULD be only one
        # of these, we hope).
        correct_indices = np.transpose(np.nonzero(self.timestamps == time_in_ns))
        num_matches = correct_indices.shape[0]
        if num_matches == 0:
            # nothing round
            raise ValueError("no entry for time %d" % time_in_ns)
        elif num_matches > 1:
            raise ValueError("multiple entries for timestamp %d" % time_in_ns)
        else:
            # We have exactly one match, which is what we want
            correct_index = correct_indices[0, 0]

        # Use our overloaded __getitem__ methods
        return self[correct_index]

    def check_time_in_range(self, time_in_ns):
        """Makes sure time is valid"""
        if not (self.timestamps[0] <= time_in_ns <= self.timestamps[-1]):
            raise ValueError("time of %d ns is out of range" % time_in_ns)

    def first_reading_below(self, time_in_ns):
        """Return the value in nanoseconds and the index for the closest sample
        to the asked for time, but earlier (or at the same time)"""

        idx_below = np.nonzero(self.timestamps <= time_in_ns)[0].max()

        return self.timestamps[idx_below], idx_below

    def first_reading_above(self, time_in_ns):
        """Return the value in nanoseconds and the index for the first sample we have
        at a time strictly greater than"""

        # Check for edge case - when we are asked for exactly the final timestamp
        if time_in_ns == self.timestamps[-1]:
            return time_in_ns, self.timestamps.size

        # If we are here, then we know that since we have already tested for validity
        # of the time, and we've checked that we aren't equal to the final time..
        # therefore there will definitely be at least one timestamp greater than
        # what we have
        idx_above = np.nonzero(self.timestamps > time_in_ns)[0].min()

        return self.timestamps[idx_above], idx_above

    def interpolated_reading_at_time(self, time_in_ns):
        """Linearly interpolate between datapoints given some time in nanoseconds.
        Note that this does naive t * data[i] + (1-t)*data[i+1] which isn't correct
        for rotation matrices. However James did this in his code and it worked out okay.."""

        self.check_time_in_range(time_in_ns)

        # Find the nanosecond readings above and below what has been requested
        nanoseconds_above, nano_above_idx = self.first_reading_above(time_in_ns)
        nanoseconds_below, nano_below_idx = self.first_reading_below(time_in_ns)

        print ("want reading at %d, got [%d,%d] and [%d,%d]" %
               (time_in_ns, nanoseconds_below, nano_below_idx,
                nanoseconds_above, nano_above_idx))

        diff = float(nanoseconds_above - nanoseconds_below)

        # t is the proportion (in the range [0,1]) which we are interpolating from
        # between the above and below readings. If time_in_ns is exactly equal to
        # nanoseconds_below then t will equal zero, if it is equal to nanoseconds_above
        # then t will be one.
        t = (time_in_ns - nanoseconds_below) / diff

        print "t = %f" % t

        return (t * self[nano_below_idx]) + ((1.0 - t) * self[nano_above_idx])


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

    def num_readings(self):
        return len(self.data)

    def total_time(self):
        """Since we may not necessarily have two lines, need to be ready
        for the possibility that we don't know how much time has passed."""
        timestamps = [d[0] for d in self.data]

        if len(timestamps) > 1:
            return timestamps[-1] - timestamps[0]
        else:
            # return -1 if we only have one measurement, and therefore
            # nothing to take difference between.
            return -1


class RecordStartStop(TimestampedData):
    def __init__(self, fname):
        with open(fname, 'r') as f:
            lines = f.readlines()

        # Strip comments
        lines = [l for l in lines if not l.startswith('//')]

        if len(lines) != 2:
            raise ValueError('was expecting 2 non-comment lines in %s' % fname)

        start_line, end_line = lines

        self.start_ns, self.start_ms_since_epoch, self.start_date = self._process(start_line)
        self.end_ns, self.end_ms_since_epoch, self.end_state = self._process(end_line)

        # Make an array
        self.timestamps = np.array([self.start_ns, self.end_ns])

    def _process(self, data_line):
        event_type, time_in_ns, wallclock_since_epoch_ms, date = data_line.split("::")

        if event_type not in ["Start", "Stop"]:
            raise ValueError("a line in RecordingStartStop_ which begins with something other than 'Start' or 'Stop'")

        # Cast the time values to integers
        return int(time_in_ns), int(wallclock_since_epoch_ms), date

    def __getitem__(self, key):
        return self.timestamps[key]  # just return the NS value


class Timestamped4Vec(TimestampedData):
    def __init__(self, fname):
        with open(fname, 'r') as f:
            lines = f.readlines()

        split_lines = [l.split(",")[:-1] for l in lines]
        self.timestamps = np.array([int(ts[0]) for ts in split_lines], dtype=np.int64)

        self.data = np.array([[float(f) for f in ts[1:]] for ts in split_lines],
                             dtype=np.float64)

    def __getitem__(self, key):
        # Allows us to index the object to get the relevant row of data,
        # which is surely what we want.
        return self.data[key, :]


class TimestampedMtx(TimestampedData):
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
        self.data = [np.array([float(r) for r in mtx]) for mtx in rot_matrices_str]
        self.data = [m.reshape(4, 4) for m in self.data]

    def __getitem__(self, key):
        # Return the relevant matrix
        return self.data[key]


class IMUSensorVideo(object):
    def __init__(self, vid_filename):
        self.vid_filename = vid_filename

        base_dir, vid_file_name = os.path.split(os.path.abspath(vid_filename))

        self.sensor_files = []

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
            h = handler(full_fname)

            # Store both as an attribute and in a list so we can iterate over
            # all the things which come from sensor files
            self.__dict__[python_name] = h
            self.sensor_files.append(h)

    def all_times_passed(self):
        return [sf.total_time() for sf in self.sensor_files]


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
        ("RecordingStartStop_", "video_timing", RecordStartStop),
        ("CameraParams_", "camera_params", CameraParams),
    ]

    def __init__(self, vid_filename):
        super(HTC1XVid, self).__init__(vid_filename)

    def rotation_matrix_at_time(self, time_in_ns):
        """Get the rotation matrix at the given time in ns"""
        return self.rot.interpolated_reading_at_time(time_in_ns)
