import maya.cmds as cmds

from Workshop.maya_api.node import BlendTwoAttrNode, ConditionNode, DistanceBetweenNode, MultiplyDivideNode, SumNode

def build_stretchy_ik(
            name: str,
            root_reference: str,
            ik_control: str,
            upper_joint: str,
            lower_joint: str,
            end_joint: str,
            stretch_attr: str = "stretch",
            drive_length_joint:bool = False,
            len_joint:str = '',
            down_axis:str='Y'
        ):
            """Build a basic non-compressing stretchy IK setup.

            Assumes the limb joints extend along local translate X.
            """

            if not cmds.attributeQuery(stretch_attr, node=ik_control, exists=True,):
                cmds.addAttr(
                    ik_control,
                    longName=stretch_attr,
                    attributeType="double",
                    minValue=0.0,
                    maxValue=1.0,
                    defaultValue=.2,
                    keyable=True,
                )

            upper_length = cmds.getAttr(f"{lower_joint}.translate{down_axis}")
            lower_length = cmds.getAttr(f"{end_joint}.translate{down_axis}")

            original_length = abs(upper_length) + abs(lower_length)

            ik_distance = DistanceBetweenNode(name=f"{name}_stretch_distance")

            ik_distance.input_matrix1.connect_from(f"{root_reference}.worldMatrix[0]")
            ik_distance.input_matrix2.connect_from(f"{ik_control}.worldMatrix[0]")

            ratio = MultiplyDivideNode(name = f"{name}_stretch_ratio")
            ratio.operation.set(2)
            ratio.input2.x.set(original_length)
            ratio.input1.x.connect_from(ik_distance.distance)

            clamp = ConditionNode(name=f"{name}_stretch_condition")
            clamp.operation.set(2)
            clamp.second_term.set(1)
            clamp.color_if_false.r.set(1)
            clamp.first_term.connect_from(ratio.output.x)
            clamp.color_if_true.r.connect_from(ratio.output.x)
            
            blend = BlendTwoAttrNode(name=f"{name}_stretch_blend")
            blend.input[0].set(1)
            blend.input[1].connect_from(clamp.out_color.r)
            blend.blend.connect_from(f"{ik_control}.{stretch_attr}")

            length = MultiplyDivideNode(name=f"{name}_stretch_lengths")
            length.input1.x.set(upper_length)
            length.input1.y.set(lower_length)
            length.input2.x.connect_from(blend.output)
            length.input2.y.connect_from(blend.output)
            length.output.x.connect_to(f"{lower_joint}.translate{down_axis}",)
            length.output.y.connect_to(f"{end_joint}.translate{down_axis}",)

            if drive_length_joint:
                len_mult = MultiplyDivideNode(name=f"{name}_ik_len")
                if upper_length >= 0:
                    mod = 1
                elif upper_length < 0:
                    mod = -1
                len_mult.input1.x.connect_from(ik_distance.distance)
                len_mult.input2.x.set(mod)

                len_sum = SumNode(name = f"{name}_limb_len")
                len_sum.input[0].connect_from(length.output.x)
                len_sum.input[1].connect_from(length.output.y)

                len_clamp = ConditionNode(name=f"{name}_stretch_condition_len")
                len_clamp.first_term.connect_from(ratio.output.x)
                len_clamp.second_term.set(1)
                len_clamp.color_if_true.r.connect_from(len_sum.output)
                len_clamp.color_if_false.r.connect_from(len_mult.output.x)
                len_clamp.operation.set(2)

                len_clamp.out_color.r.connect_to(f'{len_joint}.translate{down_axis}')