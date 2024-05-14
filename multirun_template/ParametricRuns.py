# !/bin/python3

import os
import subprocess
import logging
import fileinput
from colorlog import ColoredFormatter


CASE_NAME = "ordered_array"
TEMPALTE_DIR = "case_template"
RES = [
    1e-2,
    1,
    10,
]
ALPHAS = [
    1e-3,
    1e-2,
    # 1e-1,
]
LAMBDAS = [
    0,
    1e-2,
]
CELLS_PER_DIAMETER = 20

SBATCH_MODE = False

DRY_RUN = False

RUN_MESHING = True
RUN_CASES = True

LOG_TO_CONSOLE = True
LOG_SOURCE_LOCATION = False
MESHING_SCRIPT = "launchOFOrderedMeshing.sh"


def setup_logging(log_file, log_to_console=LOG_TO_CONSOLE):
    """setup logging to file and optionally to the console"""
    # create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # create a file handler
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
    # create a logging format
    LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - {%(filename)s:%(lineno)d in %(funcName)s()} - %(message)s"
    formatter = logging.Formatter(LOGFORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if log_to_console:
        # try and import color_log and if not dont use it
        has_color_output = True
        try:
            import color_log
        except ImportError:
            has_color_output = False
        if has_color_output:
            LOGFORMAT = "%(log_color)s%(levelname)-8s%(reset)s| %(log_color)s%(message)s%(reset)s"
            formatter = ColoredFormatter(LOGFORMAT)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


LOGGER = setup_logging("log.txt")


def replace_in_file(file, old, new):
    for line in fileinput.input(file, inplace=True):
        print(line.replace(old, new), end="")


def run_command(command, log=True):
    # if Python version is 3.5 or greater
    results = subprocess.run(
        command.split(), capture_output=True, text=True, check=False
    )
    # if Python version is 3.4 or lower
    # results = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    # LOGGER.info("Executed command : '%s' \nwhich outputted \n\t%s", command, repr(results.stdout))
    if log:
        # LOGGER.info("Executed command : '%s'", command)
        if results.returncode != 0:
            LOGGER.error(" '%s' failed with error : %s", command, results.stderr)
            return results.returncode
        else:
            LOGGER.info(
                " '%s' executed successfully with output : %s", command, results.stdout
            )

    return results.stdout


def setup_parameters(Re, Alpha, Lambda):
    """define a fuction that is run for each case that takes in the directory of the case"""
    # replace the proper parameters
    replace_in_file("paramsDict", "alpha 1e-4;", f"alpha {format_float(Alpha)};")
    replace_in_file("paramsDict", "Re 1e-2;", f"Re {format_float(Re)};")
    replace_in_file(
        "paramsDict",
        "NavierSlipLenght 1e-2;",
        f"NavierSlipLenght {format_float(Lambda)};",
    )


def create_dir_if_necessary(dir):
    """create a new directory if it does not exist"""
    if not os.path.isdir(dir):
        os.mkdir(dir)
        LOGGER.info(f"Created new directory {dir} ...")
    else:
        LOGGER.info(f"Directory {dir} already exists ...")
    return


def format_float(f):
    if f == 0:
        return "0"
    a = "%e" % f
    return a.split("e")[0].rstrip("0").rstrip(".") + "e" + a.split("e")[1]


def cd(dir):
    os.chdir(dir)
    LOGGER.debug(f"Changed directory to {os.path.abspath(dir)} ...")
    return


def cp(src, dest):
    run_command(f"cp -r {src} {dest}")
    # LOGGER.debug(f"Copied {src} to {dest} ...")
    return


def launch_sbatch(script_name):
    # launch an sbatch script and return the job ID
    out = run_command(f"sbatch {script_name}")
    id = float(out.split()[3])
    return id


def generate_mesh(alpha):
    # check if mesh already exists
    if os.path.isdir("mesh"):
        # TODO(Kamel): maybe check if valid mesh first ?
        LOGGER.info("Mesh already exists, skipping ...")
        return
    # if this is a new alpha, we need first to copy the template
    cp(f"../{TEMPALTE_DIR}", "mesh")
    cp(f"../common/.", "mesh/.")

    # update the alpha
    replace_in_file("mesh/paramsDict", "alpha 1e-4;", f"alpha {format_float(alpha)};")
    replace_in_file(
        "mesh/paramsDict",
        "CellsPerDiameter 15;",
        f"CellsPerDiameter {format_float(CELLS_PER_DIAMETER)};",
    )

    # run the mesh generation
    if not RUN_MESHING:
        LOGGER.info("Skipping mesh generation alpha = %s", alpha)
        return
    if DRY_RUN:
        LOGGER.info("Meshing for alpha = %s", alpha)
        return
    if SBATCH_MODE:
        LOGGER.info("launching meshing job for alpha = %s", alpha)
        launch_sbatch(f"mesh/{MESHING_SCRIPT}")
    else:
        LOGGER.info("meshing for alpha = %s", alpha)
        run_command("./mesh/PrepareCase")
    return


def launch_case(dir, Re, alpha, lambda_):
    # check if the case already exists
    if os.path.isdir(dir):
        LOGGER.info(f"Case {dir} already exists, skipping ...")
        return
    # create the case directory
    # create_dir_if_necessary(dir)
    # cd(dir)
    cp(f"../../../{TEMPALTE_DIR}/.", ".")
    cp(f"../../../common/.", ".")
    # run_command(f"ls ../../../")
    # setup the parameters
    setup_parameters(Re, alpha, lambda_)
    # run the case
    if not RUN_CASES:
        LOGGER.info(
            "Skipping case Re = %s, alpha = %s, lambda = %s", Re, alpha, lambda_
        )
        return
    if DRY_RUN:
        LOGGER.info("Running case Re = %s, alpha = %s, lambda = %s", Re, alpha, lambda_)
        return
    if SBATCH_MODE:
        launch_sbatch("launchOF.sh")
    else:
        # run_command("ls")
        run_command("./CleanExceptMesh")
        run_command("./AllrunParallel")
    return


def launch_cases(Res, Lambdas):
    """a function to launch a collection of cases (i.e a parametric run with the same volume fraction/mesh)"""
    if DRY_RUN:
        LOGGER.info("Running case Re = %s, alpha = %s, lambda = %s", Re, alpha, lambda_)
        return
    if SBATCH_MODE:
        launch_sbatch("launchOF.sh")
    else:
        # run_command("ls")
        run_command("./CleanExceptMesh")
        run_command("./AllrunParallel")
    return


if __name__ == "__main__":
    for alpha in ALPHAS:
        alpha_dir = f"alpha_{format_float(alpha)}"
        create_dir_if_necessary(alpha_dir)
        cd(alpha_dir)
        # ²generate the mesh for the given alpha
        generate_mesh(alpha)
        launch_cases(alpha_dir, RES, LAMBDAS)
        # for lambda_ in LAMBDAS:
        #      lambda_dir = f"lambda_{format_float(lambda_)}"
        #      create_dir_if_necessary(lambda_dir)
        #      cd(lambda_dir)
        #      run_command("pwd")
        #      for Re in RES:
        #           re_dir = f"Re_{format_float(Re)}"
        #           cp(r"../mesh",re_dir)
        #           cd(re_dir)
        #           launch_case(f"{alpha_dir}/{lambda_dir}/{re_dir}",Re,alpha,lambda_)
        #           cd("..")
        #      cd("..")
        cd("..")
