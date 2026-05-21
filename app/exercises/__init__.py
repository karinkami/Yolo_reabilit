from app.exercises.arm_raise import ArmRaiseExercise
from app.exercises.breathing_arms import BreathingArmsExercise
from app.exercises.breathing_arms_slow import BreathingArmsSlowExercise
from app.exercises.elbow_flexion import ElbowFlexionExercise
from app.exercises.forward_raise import ForwardRaiseExercise
from app.exercises.knee_extension import KneeExtensionExercise
from app.exercises.partial_squat import PartialSquatExercise
from app.exercises.recovery_abduction import RecoveryAbductionExercise
from app.exercises.scaption_raise import ScaptionRaiseExercise
from app.exercises.shoulder_abduction import ShoulderAbductionExercise

EXERCISES = {
    "shoulder_abduction": ShoulderAbductionExercise,
    "recovery_abduction": RecoveryAbductionExercise,
    "forward_raise": ForwardRaiseExercise,
    "scaption_raise": ScaptionRaiseExercise,
    "arm_raise": ArmRaiseExercise,
    "breathing_arms": BreathingArmsExercise,
    "breathing_arms_slow": BreathingArmsSlowExercise,
    "partial_squat": PartialSquatExercise,
    "elbow_flexion": ElbowFlexionExercise,
    "knee_extension": KneeExtensionExercise,
}


def get_exercise(name):
    exercise_class = EXERCISES.get(name, ShoulderAbductionExercise)
    return exercise_class()
