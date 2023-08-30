import os
import json
import subprocess
import tempfile


def test_output():
    """Test the output command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        commands = [
            ["codecarto", "output"],
            ["codecarto", "-s", temp_dir],
            ["codecarto", "--set", temp_dir],
            ["codecarto", "-r"],
            ["codecarto", "--reset"],
        ]

        for command in commands:
            result = subprocess.run(
                command, input="y\n", capture_output=True, text=True
            )

            if command == ["codecarto", "output"]:
                # check output directory prints
                assert "Current output directory: " in result.stdout
                # get the path
                path = result.stdout.split("Current output directory: ")[1]
                path = path[:-1] 
                # check if the path exists
                assert os.path.exists(path)
            elif command == ["codecarto", "-s", temp_dir] or command == [
                "codecarto",
                "--set",
                temp_dir,
            ]:
                # set output directory
                assert "Output directory changed to " in result.stdout
                # get the path
                path = result.stdout.split("Output directory changed to ")[1]
                path = path[:-1] 
                # check if the path exists
                assert os.path.exists(path)
            elif command == ["codecarto", "-r"] or command == ["codecarto", "--reset"]:
                # reset output directory
                assert "Output directory reset to " in result.stdout 
                # get the path
                path = result.stdout.split("Output directory reset to ")[1]
                path = path[:-1] 
                # check if the path exists
                assert os.path.exists(path)

            # check the config file
            # get the config file in the \src\codecarto\ directory
            config_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "src\\codecarto\\config.json",
            )
            with open(config_file, "r") as f:
                config = json.load(f)
            # check if the output directory is the same as the one in the config file
            assert config["output_dir"] == path


def test_output_dir_yes():
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_dir = os.path.join(temp_dir, "not_here")
        command = ["codecarto", "output", "-s", non_existent_dir]

        # Run the command and send the input "y\n"
        result = subprocess.run(
            command, input="y\n", text=True, capture_output=True, shell=True
        )

        # Check if the output contains the expected prompt question and response
        assert (
            "The new output directory does not exist. Would you like to make it? (y/n)"
            in result.stdout
        )
        assert f"Output directory changed to '{non_existent_dir}'" in result.stdout


def test_output_dir_no():
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_dir = os.path.join(temp_dir, "not_here")
        command = ["codecarto", "output", "-s", non_existent_dir]

        # Run the command and send the input "n\n"
        result = subprocess.run(
            command, input="n\n", text=True, capture_output=True, shell=True
        )

        # Check if the output contains the expected prompt question and response
        assert (
            "The new output directory does not exist. Would you like to make it? (y/n)"
            in result.stdout
        )
        assert "Exiting" in result.stdout
