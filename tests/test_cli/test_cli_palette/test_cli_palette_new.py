import os
import subprocess
import tempfile 

def test_palette_new():
    """Test the palette new command."""
    with tempfile.TemporaryDirectory() as temp_dir: 

#TODO: set up a test default_config.json file in the temp_dir
# difficult to use the codecarto from temp dir or nox env
# because the codecarto is installed in the base env
# need to change this so that when the codecarto is installed
# it will set up default_config.json, don't want to save it in the repo

########### Helper functions ###########
# have to create these here to maintain 
# the scope of the temp_file_path variable

        def assert_result(expected, actual):
            try:
                assert str(expected) in str(actual) 
            except AssertionError as e:
                raise AssertionError(f"Error in test_cli_palette_new.py: "  
                                        f"\n\nExpected:\n---------\n{expected}\n"
                                        f"\n\nActual:\n-------\n{actual}\n"
                                        )

        def get_palette_data():
            """Return the palette data."""
            import json

            # get the palette data from the temp_palette_new.json file
            with open(temp_file_path, "r") as f:
                palette_data = json.load(f) 
            return palette_data
        
        def check_new_data(command):
            """Check that the new type is in palette.json and has correct params.""" 

            palette_data = get_palette_data() 
            for command in commands:
                assert_result(command[3],palette_data["bases"])
                assert_result(command[5],palette_data["labels"])
                assert_result(command[6],palette_data["shapes"])
                assert_result(command[7],palette_data["colors"])
                assert_result(int(command[8])*100,palette_data["sizes"])
                assert_result(round(0.1 * int(command[9]), ndigits=1),palette_data["alphas"])

        def check_output(command, result, input:str = ""):
            """Check the output of the command."""

            actual_output = result.stdout 
 
            if input == "": 
                # check that the new type added prompt is in the output
                assert_result((f"\nNew theme added to palette: {temp_file_path}"),actual_output) 
                assert_result((f"New theme '{command[3]}' created with parameters: "
                        f"base={command[4]}, label={command[5]}, shape={command[6]}, color={command[7]}, "
                        f"size={(int(command[8])*100)}, alpha={round(0.1 * int(command[9]), ndigits=1)}\n"),actual_output) 
            elif input == "n\n":
                assert_result((f"\n{command[3]} already exists. \n " 
                        f"base:{command[4]}"
                        f"label:{command[5]}"
                        f"shape:{command[6]}"
                        f"color:{command[7]}"
                        f"size={(int(command[8])*100)}, alpha={round(0.1 * int(command[9]), ndigits=1)}\n"
                        f"\n\nOverwrite? Y/N "),actual_output) 
            elif input == "y\n":
                assert_result((f"\n{command[3]} already exists. \n " 
                        f"base:{command[4]}"
                        f"label:{command[5]}"
                        f"shape:{command[6]}"
                        f"color:{command[7]}"
                        f"size={(int(command[8])*100)}, alpha={round(0.1 * int(command[9]), ndigits=1)}\n"
                        f"\n\nOverwrite? Y/N "),actual_output) 
                assert_result((f"\nNew theme added to palette: {temp_file_path}"),actual_output) 
                assert_result((f"New theme '{command[3]}' created with parameters: "
                        f"base={command[4]}, label={command[5]}, shape={command[6]}, color={command[7]}, "
                        f"size={(int(command[8])*100)}, alpha={round(0.1 * int(command[9]), ndigits=1)}\n"),actual_output) 
        def get_config_prop(_prop_name:str):
            """Get the config properties."""
            from codecarto import Config 
            return Config().config_data[_prop_name]
        
        def set_config_prop(_prop_name:str, _value:str = "reset"):
            """Set the config properties."""
            from codecarto import Config 
            if _value == "reset":
                Config().reset_config_data()
            else:
                Config().set_config_property(_prop_name, _value)  

        def reset_palette_manually(temp_file_path):
            """Reset the palette manually."""
            import os
            import shutil
            
            # get the default palette
            default_palette_path = get_config_prop("default_palette_path") 
            
            # delete the appdata palette
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            # copy the default palette to the appdata directory
            shutil.copy(default_palette_path, temp_file_path)

        def check_palette_matches_default(temp_file_path) -> bool:
            """Check if the palette is the same as the default palette."""
            import json
            
            # get the default palette
            default_palette_path = get_config_prop("default_palette_path") 

            # check if the palette file is the same as the default palette
            with open(default_palette_path, "r") as f:
                default_palette = json.load(f)
            with open(temp_file_path, "r") as f:
                appdata_palette = json.load(f)
            if default_palette == appdata_palette: 
                return True
            else: 
                return False
            

########### Test functions ###########


        # create a temporary file for palette.json
        temp_file_name = "test_palette_new.json"
        temp_file_path = os.path.join(temp_dir, temp_file_name)

        set_config_prop("palette_file_name", temp_file_name)
        set_config_prop("palette_dir", temp_dir)

        # Make the directory if it doesn't exist
        os.makedirs(os.path.dirname(temp_dir), exist_ok=True)

        # define commands for new palette and checks
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
        for command in commands: 
            # before starting reset palette manually, to keep the tests isolated
            reset_palette_manually(temp_file_path)
            if not check_palette_matches_default(temp_file_path):
                raise Exception("Setting up test for 'palette new' failed.")
            # run command
            result = subprocess.run(command, capture_output=True, text=True) 
            # check output
            check_output(command, result)
            # check that new type in palette.json and has correct params
            check_new_data(command)
            # change type color
            _old_color = command[7]
            command[7] = "green"
            # run command again to check that overwrite prompt worksl, input 'n'
            result = subprocess.run(command, input="n\n", capture_output=True, text=True) 
            # check output
            check_output(command, result)
            # change type color back for check
            command[7] = _old_color
            # check that new type is still in palette.json and color is not changed 
            check_new_data(command)
            # run command again to check that overwrite prompt works, input 'y'
            command[7] = "yellow"
            result = subprocess.run(command, input="y\n", capture_output=True, text=True) 
            # check output
            check_output(command, result)
            # check that new type is still in palette.json and color is changed
            check_new_data(command)

