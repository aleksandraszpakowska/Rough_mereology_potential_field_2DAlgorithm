import math
from le_mind_controller.MindData import MindData, HubPortName
from le_mind_controller.MindComm import MindComm
from le_mind_controller.Helpers import Helpers
import cv2
import numpy as np

center_point = [0, 0]
size_from_pygame_chart = (542, 373)

def read_coordinates(file_name):
    with open(file_name) as file:
        coordinates = []
        for line in file:
            row = line.split()
            x = row[0]
            y = row[1]
            coordinates.append((float(x), float(y)))
    return coordinates

def convert(k,x):
    x = x - k
    if x > 180:
        x = x - 360
    if x < -180:
        x = 360 + x
    return x


def color_detection(frame):
    global center_point #define a global value
    kernel = np.ones((2, 2), np.uint8)
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    a_channel = lab[:, :, 1]

    ret, thresh = cv2.threshold(a_channel, 105, 255, cv2.THRESH_BINARY_INV)  # to binary
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_GRADIENT, kernel)  # to get outer boundery only

    thresh = cv2.dilate(thresh, kernel, iterations=5)  # to strength week pixels
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if len(contours) > 0:
        # find the biggest countour (c) by the area
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        x1 = x + w
        y1 = y + h
        # draw the biggest contour (c) in green
        cv2.rectangle(frame, (x, y), (x1, y1), (255, 0, 0), 2)
        center_point = [int((x + x1) / 2), int((y + y1) / 2)] #still updating the global value
        # coordinates of the rectangle

        #print("Center point funct: ", center_point)

goal_ = read_coordinates('../old_paths/v1/goal_coords.txt')
start_ = read_coordinates('../old_paths/v1/start_coords.txt')
path_ = read_coordinates('../old_paths/v1/path_coords.txt')

x_start, y_start = zip(*start_)
x_goal, y_goal = zip(*goal_)

x_stop = x_goal[0]
y_stop = y_goal[0]

path_points_x, path_points_y = zip(*path_)

ksi = 0.6
beta = 0.1
k1 = 50
k2 = 50
precision = 20

print("Available COM ports:")
for prt in Helpers.get_available_ports():
    print(prt)

port = input("Selected COM port: ")
ser = Helpers.create_serial(port)
md = MindData()
mc = MindComm(ser, md)

while not mc.data_received:
    pass
mc.start_command_streaming()

print("Number of devices connected to the hub: {}".format(md.determine_type_of_connected_devices()))

import time
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, size_from_pygame_chart[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size_from_pygame_chart[1])

normalizing_ = read_coordinates('../old_paths/v1/normalizing_coord.txt')
x_min, y_min = zip(*normalizing_)


while True:

    for i in range(len(path_)):
        _, frame = cap.read()
        # cv2.imshow("Frame", frame)
        color_detection(frame)
        actual_x = center_point[0] - x_min[0]
        actual_y = center_point[1] - y_min[0]

        temp_direction = md.tilt_angle[0]

        act_dir = math.atan2(path_points_x[i] - actual_y, path_points_y[i] - actual_x) * 180 / 3.14
        cte = convert(act_dir, temp_direction)

        #print("Actual center:", actual_x, actual_y)
        #print("Path points: ", path_points_x[i], path_points_y[i])
        print("tilt angle: ", temp_direction)
        print("new direction: ", act_dir)
        print(cte)

        if cte <= 0:
            if abs(cte) > precision:
                k2 = (k1 * (-1))
            else:
                k2 = (k1 * (-1)) + (ksi * cte)

        if cte > 0:
            if cte > precision:
                k1 = (k2 * (-1))
            else:
                k1 = (k2 * (-1)) - (ksi * cte)

        print("Speed k1 = ", k1, "Speed k2 = ", k2)
        # function for turning left\right with respecting the degree
        mc.motor_double_turn_on_deg(HubPortName.A, HubPortName.B, k2, k1, degrees=act_dir)
        time.sleep(5)  # waiting

        # function for moving forward with given distance
        mc.motor_double_turn_on(HubPortName.A, HubPortName.B, abs(k2), abs(k1), distance_cm=15)
        time.sleep(5)  # waiting

        if i == len(path_) - 1:
            mc.stop_program_execution()

    if cv2.waitKey(1) & 0xFF == ord('d'):
        break

cap.release()
cv2.destroyAllWindows()