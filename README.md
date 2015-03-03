# Medical-3D-Printing
Project I worked on for a year and a half during my undergrad, coded fully in python . The Project is used to create 3d printed moulds from a patients X-ray CT scans. These moulds lay on plastic mesh and deliver radiation therapy.

## ThermoPlastic Meshes
<img src="https://raw.githubusercontent.com/Mark-William-Schumacher/Medical-3D-Printing/master/HDRMask/Pictures/3DModel.jpg" height=250px >

This is an example of the thermoplastic mesh we build the 3D moulds on, after taking any x-ray scan of this mesh, we can build a closed surface model and then generate a perfectly fitted mould to be placed on the mesh.

<img src="https://raw.githubusercontent.com/Mark-William-Schumacher/Medical-3D-Printing/master/HDRMask/Pictures/IMG_20150215_171654.jpg" height=250px>

## Self Designed Algorithm

![Thermoplastic Mesh](https://github.com/Mark-William-Schumacher/Medical-3D-Printing/blob/master/HDRMask/Pictures/Inputs2.gif)

The algorythm works on the a closed surface model , which can be extracted from the x-ray image files using some semi-automated segmentation algorythms . 
