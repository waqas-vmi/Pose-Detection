import cv2
import mediapipe as mp
import math
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=2,
    min_detection_confidence=0.9,
    smooth_landmarks=True,
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

def check_full_body_landmarks(landmarks):
    # Check if critical landmarks are detected (shoulders, hips, knees)
    required_landmarks = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
        mp_pose.PoseLandmark.LEFT_KNEE,
        mp_pose.PoseLandmark.RIGHT_KNEE
    ]
    
    # If any of the required landmarks are missing, return False
    for lm in required_landmarks:
        if landmarks[lm].visibility < 0.5:
            return False
    return True

def calculate_visual_bmi(declared_weight_kg, visual_height_ratio, shoulder_width_ratio):
    if visual_height_ratio <= 0 or shoulder_width_ratio <= 0:
        return {"error": "Invalid visual measurements."}
    
    # Tuned logic
    body_ratio = visual_height_ratio / shoulder_width_ratio

    # Adjust visual height with empirically tuned scaling
    visual_height_m = 1.7 + (body_ratio - 2) * 0.2  # 1.65m base + adjust slightly

    # Clamp to prevent unrealistic height
    visual_height_m = max(1.4, min(2.1, visual_height_m))

    # Calculate the visual BMI using the visual height
    visual_bmi = declared_weight_kg / (visual_height_m ** 2)
    
    return visual_bmi

def process_image(image_path):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if not results.pose_landmarks:
        return {"error": f"Pose not detected in {image_path}"}

    landmarks = results.pose_landmarks.landmark

    if not check_full_body_landmarks(landmarks):
        return {"error": f"Full-body pose required in {image_path}. Missing critical landmarks."}

    orientation = validate_image_orientation(landmarks)

    # Extract key points
    nose = landmarks[mp_pose.PoseLandmark.NOSE]
    heel_left = landmarks[mp_pose.PoseLandmark.LEFT_HEEL]
    heel_right = landmarks[mp_pose.PoseLandmark.RIGHT_HEEL]
    shoulder_left = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    shoulder_right = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    # Visual height
    head_to_heel_y = max(heel_left.y, heel_right.y) - nose.y
    visual_height_ratio = abs(head_to_heel_y)

    # Shoulder width (3D)
    shoulder_width = math.sqrt(
        (shoulder_right.x - shoulder_left.x) ** 2 +
        (shoulder_right.y - shoulder_left.y) ** 2 +
        (shoulder_right.z - shoulder_left.z) ** 2
    )

    return {
        "visual_height_ratio": visual_height_ratio,
        "shoulder_width_ratio": shoulder_width,
        "orientation": orientation
    }

def calculate_bmi_from_images(back_image_path, front_image_path, declared_height_cm, declared_weight_kg):

    # Process both images
    front_data = process_image(front_image_path)
    back_data = process_image(back_image_path)

    # Check for errors
    if "error" in front_data:
        return front_data
    if "error" in back_data:
        return back_data

    # Average the measurements
    avg_height_ratio = (front_data["visual_height_ratio"] + back_data["visual_height_ratio"]) / 2
    avg_shoulder_width = (front_data["shoulder_width_ratio"] + back_data["shoulder_width_ratio"]) / 2

    # Declared BMI
    height_m = declared_height_cm / 100
    declared_bmi = round(declared_weight_kg / (height_m ** 2), 2)

    # BMI category
    if declared_bmi < 18.5:
        bmi_category = "Underweight"
    elif 18.5 <= declared_bmi <= 24.9:
        bmi_category = "Normal weight"
    elif 25 <= declared_bmi < 29.9:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obesity"

    # Visual BMI
    visual_bmi = calculate_visual_bmi(declared_weight_kg, avg_height_ratio, avg_shoulder_width)
    if isinstance(visual_bmi, dict) and "error" in visual_bmi:
        return visual_bmi

    # BMI verification
    bmi_difference = abs(visual_bmi - declared_bmi)
    bmi_verified = bmi_difference <= 5.0
    verification_result = "Verification passed" if bmi_verified else f"Mismatch - BMI discrepancy ({bmi_difference:.2f})"

    response = {
        "declared_bmi": declared_bmi,
        "visual_bmi": round(visual_bmi, 2),
        "input_height_cm": declared_height_cm,
        "input_weight_kg": declared_weight_kg,
        "visual_height_ratio": round(avg_height_ratio, 3),
        "shoulder_width_ratio": round(avg_shoulder_width, 3),
        "bmi_category": bmi_category,
        "orientation_front": front_data["orientation"],
        "orientation_back": back_data["orientation"],
        "verification_result": verification_result,
        "bmi_verified": bmi_verified
    }

    logging.info(f"Combined image BMI result: {response}")
    return response
