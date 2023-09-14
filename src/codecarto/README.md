For the moment, we have a 'local' and 'containers' folder to separate the two versions of codecarto.
Local is intended to be run as a local package. Containers as a web service.
Local was initially intended to be a CLI version and library for use in other projects.

At some point these will be merged and CLI will call the api in the containers.
The core logic will be moved to 'core' or something alike.
the library version will be the 'core' logic (and possibly the api)

So in the end, we will have 3 ways to use codecarto:

- Web App: api calls to core logic
- CLI: api calls to core logic
- Library: core logic (and possibly api for use in other projects)

For now, these are separated in the folders 'containers' and 'local'.
