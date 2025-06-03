import cv2
import mediapipe as mp
import math

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5
)

def validate_image_orientation(landmarks):
    if not landmarks:
        return "No body landmarks detected"

    shoulder_left = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    shoulder_right = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    hip_left = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    hip_right = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

    shoulder_distance = abs(shoulder_right.x - shoulder_left.x)
    hip_distance = abs(hip_right.x - hip_left.x)

    if shoulder_distance > 0.15 and hip_distance > 0.15:
        return "Front"
    else:
        return "Side"

def calculate_bmi(image_path, declared_height_cm, declared_weight_kg):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if not results.pose_landmarks:
        return {"error": "Pose not detected."}

    landmarks = results.pose_landmarks.landmark
    orientation = validate_image_orientation(landmarks)

    # Estimate visual height (nose to heel Y-distance, normalized 0–1)
    nose = landmarks[mp_pose.PoseLandmark.NOSE]
    heel_left = landmarks[mp_pose.PoseLandmark.LEFT_HEEL]
    heel_right = landmarks[mp_pose.PoseLandmark.RIGHT_HEEL]

    heel_y = max(heel_left.y, heel_right.y)
    visual_height_ratio = abs(heel_y - nose.y)  # ~0.6–0.9 range

    # Shoulder width for proportion comparison
    shoulder_left = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    shoulder_right = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    shoulder_width = abs(shoulder_right.x - shoulder_left.x)

    # BMI from declared values
    height_m = declared_height_cm / 100
    bmi = round(declared_weight_kg / (height_m ** 2), 2)

    return {
        "bmi": bmi,
        "input_height_cm": declared_height_cm,
        "input_weight_kg": declared_weight_kg,
        "visual_height_ratio": round(visual_height_ratio, 3),
        "shoulder_width_ratio": round(shoulder_width, 3),
        "orientation": orientation
    }
