
import maya.cmds as cmds
from Workshop.maya_api.node import ConditionNode, DistanceBetweenNode, MultiplyDivideNode



def build_compressible_ik_length(
        name: str,
        root_reference: str,
        ik_control: str,
        length_joint: str,
        down_axis: str = "Y",
    ) -> None:
        """Build a single-joint IK length that compresses but does not stretch.

        The length_joint's translate channel is shortened when the IK control
        moves closer than the original joint length. Moving farther away will
        not extend the joint beyond its original length.

        Args:
            name: Base name used for created nodes.
            root_reference: Transform marking the beginning of the chain.
            ik_control: Transform marking the desired end of the chain.
            length_joint: Joint whose translate channel controls the chain length.
            down_axis: Local joint axis used for its length.
        """
        translate_attr = f"{length_joint}.translate{down_axis}"
        original_length = cmds.getAttr(translate_attr)
        absolute_original_length = abs(original_length)

        # Preserve whether the joint extends down the positive or negative axis.
        direction = 1.0 if original_length >= 0.0 else -1.0

        distance = DistanceBetweenNode(name=f"{name}_compress_distance")
        distance.input_matrix1.connect_from(
            f"{root_reference}.worldMatrix[0]"
        )
        distance.input_matrix2.connect_from(
            f"{ik_control}.worldMatrix[0]"
        )

        # Convert the always-positive world-space distance into the joint's
        # original positive or negative translate direction.
        signed_distance = MultiplyDivideNode(
            name=f"{name}_compress_signed_distance"
        )
        signed_distance.input1.x.connect_from(distance.distance)
        signed_distance.input2.x.set(direction)

        compress_condition = ConditionNode(
            name=f"{name}_compress_condition"
        )

        # condition operation 4 means "Less Than":
        # distance < original length
        compress_condition.operation.set(4)
        compress_condition.first_term.connect_from(distance.distance)
        compress_condition.second_term.set(absolute_original_length)

        # Shorter than the original: use the measured distance.
        compress_condition.color_if_true.r.connect_from(
            signed_distance.output.x
        )

        # Longer than the original: remain at the original length.
        compress_condition.color_if_false.r.set(original_length)

        compress_condition.out_color.r.connect_to(translate_attr)