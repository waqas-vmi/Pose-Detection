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
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    # Use X-distance between shoulders for lateral spread
    x_distance = abs(right_shoulder.x - left_shoulder.x)
    
    # Use Z-depth difference to detect turning of the torso
    z_distance = abs(right_shoulder.z - left_shoulder.z)

    # Use visibility to check if both shoulders are clearly visible
    visible = left_shoulder.visibility > 0.5 and right_shoulder.visibility > 0.5

    if x_distance > 0.15 and z_distance < 0.2 and visible:
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

    # Extract key points
    nose = landmarks[mp_pose.PoseLandmark.NOSE]
    heel_left = landmarks[mp_pose.PoseLandmark.LEFT_HEEL]
    heel_right = landmarks[mp_pose.PoseLandmark.RIGHT_HEEL]
    shoulder_left = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    shoulder_right = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    # Visual height estimation (nose to heel)
    heel_y = max(heel_left.y, heel_right.y)
    visual_height_ratio = abs(heel_y - nose.y)

    # Shoulder width
    shoulder_width = abs(shoulder_right.x - shoulder_left.x)

    # Aspect ratio for visual proportion (height-to-width)
    if shoulder_width == 0:
        return {"error": "Invalid pose (shoulder width = 0)"}
    body_ratio = visual_height_ratio / shoulder_width  # taller = bigger ratio

    # Declared BMI
    height_m = declared_height_cm / 100
    declared_bmi = round(declared_weight_kg / (height_m ** 2), 2)

    # Check consistency between visual ratio and declared BMI
    # Typical body_ratio for slim ~6.5–8, average ~5–6, overweight ~4 or lower
    if body_ratio >= 6 and declared_bmi < 22:
        bmi_match = "Likely accurate (slim)"
    elif 5 <= body_ratio < 6 and 22 <= declared_bmi <= 26:
        bmi_match = "Likely accurate (average build)"
    elif body_ratio < 4.5 and declared_bmi > 27:
        bmi_match = "Likely accurate (overweight)"
    else:
        bmi_match = "Possible mismatch – verify declared height/weight"

    return {
        "declared_bmi": declared_bmi,
        "input_height_cm": declared_height_cm,
        "input_weight_kg": declared_weight_kg,
        "visual_height_ratio": round(visual_height_ratio, 3),
        "shoulder_width_ratio": round(shoulder_width, 3),
        "visual_body_ratio": round(body_ratio, 2),
        "orientation": orientation,
        "validation_result": bmi_match
    }
