# allen-to-nwb

NWB conversion scripts and tutorials. A collaboration with the [Allen Institute](https://alleninstitute.org/).

# Install
```
$ pip install git+https://github.com/catalystneuro/allen-to-nwb
```

# Use

**1. Imported and run from a python script:** <br/>
An example notebook can be found [here](https://github.com/catalystneuro/allen-oephys-to-nwb/tree/master/tutorials)


**2. Graphical User Interface:** <br/>
To use the GUI, just type in the terminal:
```shell
$ nwbgui-oephys
```
The NWB-WebGUI should open in your browser. If it does not open automatically (and no error messages were printed in your terminal), just open your browser and navigate to `localhost:5000`.

The GUI eases the task of editing the metadata of the resulting `nwb` file, it is integrated with the conversion module (conversion on-click) and allows for quick visual exploration the data in the end file with [nwb-jupyter-widgets](https://github.com/NeurodataWithoutBorders/nwb-jupyter-widgets).
