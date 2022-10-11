import logging
import os
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Union

logger = logging.getLogger("build-with-docker")


def main(cli_args: List[str]):
    logging.basicConfig(level=logging.DEBUG)

    parser = ArgumentParser()
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--project", type=str)
    parser.add_argument("--output", type=str,
                        default=Path(os.getcwd()) / "output")
    # Providing this parameter
    #   (a) *might* (should, but it doesn't) speed up (subsequent) builds, but
    #   (b) *might* (with a *very low* probability) break build determinism.
    # As of September 2022, both (a) and (b) are still open points.
    parser.add_argument("--cargo-target-dir", type=str)
    parser.add_argument("--no-wasm-opt", action="store_true", default=False,
                        help="do not optimize wasm files after the build (default: %(default)s)")

    parsed_args = parser.parse_args(cli_args)
    image = parsed_args.image
    project_path = Path(parsed_args.project).expanduser().resolve()
    output_path = Path(parsed_args.output).expanduser().resolve()
    cargo_target_dir = Path(parsed_args.cargo_target_dir).expanduser(
    ).resolve() if parsed_args.cargo_target_dir else None
    no_wasm_opt = parsed_args.no_wasm_opt

    output_path.mkdir(parents=True, exist_ok=True)

    return_code = run_docker(
        image, project_path, output_path, cargo_target_dir, no_wasm_opt)
    return return_code


def run_docker(image: str, project_path: Path, output_path: Path, cargo_target_dir: Union[Path, None], no_wasm_opt: bool):
    docker_mount_args = [
        "--mount", f"type=bind,source={project_path},destination=/project",
        "--mount", f"type=bind,source={output_path},destination=/output"
    ]

    if cargo_target_dir:
        docker_mount_args += ["--mount",
                              f"type=bind,source={cargo_target_dir},destination=/cargo-target-dir"]

    docker_args = ["docker", "run"] + docker_mount_args + ["--rm", image]

    entrypoint_args = [
        "--output-owner-id", str(os.getuid()),
        "--output-group-id", str(os.getgid())
    ]

    if no_wasm_opt:
        entrypoint_args.append("--no-wasm-opt")

    args = docker_args + entrypoint_args
    logger.info(f"Running docker: {args}")

    result = subprocess.run(args)
    return result.returncode


if __name__ == "__main__":
    return_code = main(sys.argv[1:])
    exit(return_code)