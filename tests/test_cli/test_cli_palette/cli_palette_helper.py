def get_palette_data(item: str, appdata: bool = True) -> dict | str:
    """Load the palette data from the Palette class."""
    from codecarto import Palette

    if item == "bases":
        return Palette().get_palette_data()
    elif item == "path" and appdata is True:
        return Palette()._palette_app_dir[item]
    elif item == "path" and appdata is False:
        return Palette()._palette_pack_dir[item]
 
def check_palette_matches_default() -> bool:
    """Check if the palette is the same as the default palette."""
    import json
    
    # get the default palette
    default_palette_path = get_palette_data("path", False)

    # get the appdata palette
    appdata_palette_path = get_palette_data("path")

    # check if the palette file is the same as the default palette
    with open(default_palette_path, "r") as f:
        default_palette = json.load(f)
    with open(appdata_palette_path, "r") as f:
        appdata_palette = json.load(f)
    if default_palette == appdata_palette: 
        return True
    else: 
        return False
    
def reset_palette_manually():
    """Reset the palette manually."""
    import os
    import shutil
    
    # get the default palette
    default_palette_path = get_palette_data("path", False)

    # get the appdata palette
    appdata_palette_path = get_palette_data("path")

    # delete the appdata palette
    os.remove(appdata_palette_path)

    # copy the default palette to the appdata directory
    shutil.copy(default_palette_path, appdata_palette_path)

def set_config_prop(_prop_name:str, _value:str = "reset"):
    """Set the config properties."""
    from codecarto import Config 
    if _value == "reset":
        Config().reset_config_data()
    else:
        Config().set_config_property(_prop_name, _value) 
    