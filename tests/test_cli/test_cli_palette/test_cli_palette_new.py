import os
import subprocess
import tempfile
from cli_palette_helper import get_palette_data


def test_palette_new():
    """Test the palette new command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_new.json")

        def run_commands_and_check_output(commands):
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True)
                expected_strings = [
                    f"New theme added to palette: ",
                    (
                        f"New theme '{command[3]}' "
                        f"created with parameters: "
                        f"base={command[4]}, "
                        f"label={command[5]}, "
                        f"shape={command[6]}, "
                        f"color={command[7]}, "
                        f"size={command[8]}, " # TODO this needs to be converted from 1-10 to 100-1000
                        f"alpha={command[9]}" # TODO this needs to be converted from 1-10 to 0.1-1.0
                    ),
                ]
                for string in expected_strings:
                    assert string in result.stdout

        def check_palette_data(commands, presence=True):
            palette_data = get_palette_data

            for command in commands:
                assert (command[4] in palette_data["bases"]) == presence
                assert (command[5] in palette_data["labels"]) == presence
                assert (command[6] in palette_data["shapes"]) == presence
                assert (command[7] in palette_data["colors"]) == presence
                assert (command[8] in palette_data["sizes"]) == presence
                assert (command[9] in palette_data["alphas"]) == presence

        # define commands
        commands = [
            [
                "codecarto",
                "palette",
                "-n",
                "Type_Test_Short",
                "basic",
                "Label_Test_Short",
                "o",
                "red",
                "3",
                "1",
            ],
            [
                "codecarto",
                "palette",
                "--new",
                "Type_Test_Long",
                "basic",
                "Label_Test_Long",
                "s",
                "blue",
                "4",
                "2",
            ],
        ]

        # reset palette before starting for sanity check
        cmd = ["codecarto", "palette", "-r"]
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input="y\n")

        # run commands
        run_commands_and_check_output(commands)

        # check that the new themes are in the palette
        check_palette_data(commands)
        
        # TODO: add test for overwrite prompt
        # # run commands again to check that overwrite prompt works
        # run_commands_and_check_output(commands)

        # # check that the new themes are still in the palette
        # check_palette_data(commands)

        # reset palette
        #subprocess.run("codecarto", "palette", "-r", silent=True)
        cmd = ["codecarto", "palette", "-r"]
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input="y\n")

        # check that the new themes are not in the palette anymore
        check_palette_data(commands, presence=False)
