import json
import subprocess
import tempfile
from cli_palette_helper import check_palette_matches_default, get_palette_data, reset_palette_manually


def test_palette_reset():
    """Test the palette reset command with a 'y' and 'n' responses."""
    with tempfile.TemporaryDirectory() as temp_dir:  
        # define commands and responses
        commands:list = [
            ["codecarto", "palette", "-r"],
            ["codecarto", "palette", "--reset"],
        ]
        responses:list = ["y\n", "n\n"]  

        for command in commands: 
            for response in responses:  
                # need to make palette is not the same as default palette for 'n' response
                if response == "n\n":
                    # reset the palette to the default   
                    reset_palette_manually()
                    if not check_palette_matches_default(): 
                        raise Exception("Setting up test for palette reset 'n' response failed.")
                    # manually change the palette 
                    # don't use the cli, to keep the tests isolated
                    appdata_palette_path = get_palette_data("bases")
                    with open(appdata_palette_path, "r") as f:
                        appdata_palette = json.load(f)
                    appdata_palette["colors"]["unknown"] = "pink" # normally, gray
                    with open(appdata_palette_path, "w") as f:
                        json.dump(appdata_palette, f)
                    # double check if the palette is different  
                    if check_palette_matches_default(): 
                        raise Exception("Setting up test for palette reset 'n' response failed.")
 
                # Run the command and send the response 
                result = subprocess.run(
                    command, input=response, text=True, capture_output=True, shell=True
                )
                # check for reset question and repsponse
                assert "Are you sure you want to reset the palette to the default palette?\nOverwrite? Y/N" in result.stdout
                if response == "y\n": 
                    assert "Palette reset to default." in result.stdout 
                    assert check_palette_matches_default()
                elif response == "n\n": 
                    assert not check_palette_matches_default()


