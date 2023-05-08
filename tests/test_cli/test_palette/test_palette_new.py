import os
import subprocess
import tempfile
from palette_helper import get_palette_data


def test_palette_new():
    """Test the palette new command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_new.json")

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

        # run commands
        run_commands_and_check_output(commands)

        # check that the new themes are in the palette
        check_palette_data(commands)

        # reset palette
        subprocess.run("codecarto", "palette", "-r", silent=True)

        # check that the new themes are not in the palette anymore
        check_palette_data(commands, presence=False)

        def run_commands_and_check_output(commands):
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True)
                expected_strings = [
                    f"New theme added to palette: ",
                    (
                        f"New theme '{command[0]}' "
                        f"created with parameters: "
                        f"base={command[1]}, "
                        f"label={command[2]}, "
                        f"shape={command[3]}, "
                        f"color={command[5]}, "
                        f"size={command[4]}, "
                        f"alpha={command[6]}"
                    ),
                ]
                for string in expected_strings:
                    assert string in result.stdout

        def check_palette_data(commands, presence=True):
            palette_data = get_palette_data

            for command in commands:
                assert (command[0] in palette_data["bases"]) == presence
                assert (command[1] in palette_data["labels"]) == presence
                assert (command[2] in palette_data["shapes"]) == presence
                assert (command[4] in palette_data["colors"]) == presence
                assert (command[3] in palette_data["sizes"]) == presence
                assert (command[5] in palette_data["alphas"]) == presence
