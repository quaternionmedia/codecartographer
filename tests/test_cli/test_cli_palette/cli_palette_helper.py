def get_palette_data(item: str, appdata: bool = True) -> dict | str:
    """Load the palette data from the Palette class."""
    from codecarto import Palette

    if item == "bases":
        return Palette().get_palette_data()
    elif item == "path" and appdata is True:
        return Palette()._palette_app_dir[item]
    elif item == "path" and appdata is False:
        return Palette()._palette_pack_dir[item]
