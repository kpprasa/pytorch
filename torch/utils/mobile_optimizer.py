"""
This module contains utility method for mobile model optimization and lint.
"""

import torch
from enum import Enum
from torch._C import MobileOptimizerType
from typing import Dict

class LintCode(Enum):
    BUNDLED_INPUT = 1
    REQUIRES_GRAD = 2
    DROPOUT = 3
    BATCHNORM = 4

def optimize_for_mobile(script_module, whitelist_optimizer_dict: Dict[MobileOptimizerType, bool] = {}):
    """
    Args:
        script_module: An instance of torch script module with type of ScriptModule
        whitelist_optimizer_dict: A dictionary with key type of MobileOptimizerType and value type of bool.
        When dict is not passed, optimization method will run all the optimizer pass; otherwise, optimizer
        method will run the whitelist optimization pass that has value of True.
    Returns:
        script_module: A new optimized torch script module
    """
    if not isinstance(script_module, torch.jit.ScriptModule):
        raise TypeError(
            'Got {}, but ScriptModule is expected.'.format(type(script_module)))

    optimized_cpp_module = torch._C._jit_pass_optimize_for_mobile(script_module._c, whitelist_optimizer_dict)
    return torch.jit._recursive.wrap_cpp_module(optimized_cpp_module)


def generate_mobile_module_lints(script_module: torch.jit.ScriptModule):
    """
    Args:
        script_module: An instance of torch script module with type of ScriptModule

    Returns:
        lint_map: A list of dictionary that contains modules lints
    """
    if not isinstance(script_module, torch.jit.ScriptModule):
        raise TypeError(
            'Got {}, but ScriptModule is expected.'.format(type(script_module)))

    lint_list = []

    if not hasattr(script_module, "_generate_bundled_inputs"):
        lint_list.append({"name": LintCode.BUNDLED_INPUT.name, "message": "No bundled input, please add bundled inputs before "
                          "saving the module using torch.utils.bundled_inputs.augment_model_with_bundled_inputs."})

    for name, param in script_module.named_parameters():
        if param.requires_grad:
            lint_list.append({"name": LintCode.REQUIRES_GRAD.name, "message": "Param {} requires grad, "
                             "please set torch.no_grad() to reduce memory usage and improve computation speed during "
                              "inference phase.".format(name)})

    op_names = torch.jit.export_opnames(script_module)
    for op_name in op_names:
        if "dropout" in op_name:
            lint_list.append({"name": LintCode.DROPOUT.name, "message": "Operator {} exists, remember to call eval() before "
                              "saving the module.".format(op_name)})
        if "batch_norm" in op_name:
            lint_list.append({"name": LintCode.BATCHNORM.name, "message": "Operator {} exists, remember to call eval() before "
                              "saving the module and call torch.utils.mobile_optimizer.optimize_for_mobile to drop batch_norm "
                              "operator.".format(op_name)})

    return lint_list
