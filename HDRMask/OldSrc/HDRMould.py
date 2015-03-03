import os
import unittest
import numpy
import time
from __main__ import vtk, qt, ctk, slicer
import math
import HDRLib


ROOTPATH = "C:\\MakeHDRApplicatorMask\\" # This is where doc, src and data should be
PATHDEBUG= ROOTPATH+"\\doc\\DebugPolyData\\" #Where to store poldataWritter output
DEBUG_CLIPPING= False
DEBUG_CUTTINGPLANES= False
DEBUG_MINMASK= False
DEBUG_RAWPATH= False
DEBUG_SLITPLANES=True
CATHETER_DEBUG_POLYGON=False
CATHETER_DEBUG_RAW_POINTS=False #Show Raw Path Points-Costly to visualize
CATHETER_DEBUG_RAW_PATH=False
CATHETER_DEBUG_RECONSTRUCT=False
CATHETER_DEBUG_SPLINE=True
CATHETER_DEBUG_INSIDEVIOLATION=False
CATHETER_DEBUG_SHOWCIRCLES=False
CATHETER_DEBUG_MOVEDPATH=False
CATHETER_DEBUG_SMOOTHEDPATH=False
CATHETER_DEBUG_TUBE=True
CATHETER_DEBUG_CHANNEL=True
CATHETER_DEBUG_BADPOINTS=False

class HDRMould:
  """ is the hook by which the Slicer module factory recognizes the
   module and populates the menu and other internal structures. 
   This is where you customize the metadata of your module. Note that
   the self-test code is also initialized here. The constructor is 
   passed a parent, which is an instance of a qSlicerScriptedLoadableModule.
   This is not a parent in the QObject sense of the term, but it is the hook 
   that allows you to bind your python code to the corresponding C++ calls."""

  def __init__(self, parent):
    parent.title = "HDR Mould Desktop"
    parent.categories = ["Brachytherapy"]
    parent.dependencies = []
    parent.contributors = ["Mark Schumacher, Ian Cumming, \
                            Laboratory for Percutaneous Surgery"]
    parent.helpText = """
      **This scripted module creates a mask from CT scan data. 
      The user defines which face of the volume to make the mask for.
      The mask can then be cropped using other Slicer modules. <br>
      The module also carves out open channels for catheters to run through.
      The input catheter volume should have the same dimensions as the CT scan
      volume. <br>
      
      <br>
      NOTE: Upon completion the brightness and contrast of the slice viewers
      may be set to max, and need to be adjusted by clicking on the slice
       viewer and dragging up and right as needed. <br> Workflow** """
    
    parent.acknowledgementText = """
      Written by Mark Schumacher and Ian Cumming in the Laboratory for
      Percutaneous Surgery at Queen's University in Kingston,
      ON. Funded by an NSERC research grant. """
    
    self.parent = parent
    
    # Add this test to the SelfTest module's list for discovery when the 
    # module is created.  Since this module may be discovered before SelfTests
    # itself, create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['HDR Mask'] = self.runTest

  def runTest(self):
    tester = HDRMouldTest()
    tester.runTest()
    
    
    
class HDRMouldWidget:
  """The ScriptedLoadableModuleTemplateWidget defines the GUI of the module.
  The constructor is passed an instance of a 
  qSlicerScriptedLoadableModuleWidget which is a hook to C++.
  """
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()
  def setup(self):
    """Instantiate and connect widgets 
    """
    
    # Reload and Test Area
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # Reload button 
    #TODO Make is so correct models are loaded into scroll slots, its a 
    # pain to keep clicking to insert models 
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "HDRMould Reload"
    reloadFormLayout.addWidget(self.reloadButton)

    # Reload and Test button
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.setToolTip("""Reload this module and then run 
    the self tests.""")
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    
    # Make TestObject Mould - button
    self.createTestObjectButton = qt.QPushButton()
    self.createTestObjectButton.setText("Create Test Object")
    self.createTestObjectButton.toolTip = "Creates a mask of a specified \
    thickness from the face of interest. Catheter paths are carved out \
    along the line connecting the pairs of fiducials. This overwrites \
    the Output Model."
    self.createTestObjectButton.enabled = True
    reloadFormLayout.addRow(self.createTestObjectButton)

    # Parameters Area
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    #Debug Mode Check Box:
    
    
    # Layout within the collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)


    # target surface model ComboBox - drop down menu
    self.surfaceModelComboBox = slicer.qMRMLNodeComboBox()
    self.surfaceModelComboBox.nodeTypes = ( ("vtkMRMLModelNode"),"" )
    self.surfaceModelComboBox.selectNodeUponCreation = True
    self.surfaceModelComboBox.addEnabled = False
    self.surfaceModelComboBox.removeEnabled = False
    self.surfaceModelComboBox.noneEnabled = False
    self.surfaceModelComboBox.showHidden = False
    self.surfaceModelComboBox.showChildNodeTypes = False
    self.surfaceModelComboBox.setMRMLScene( slicer.mrmlScene )
    self.surfaceModelComboBox.setToolTip("Choose the skin surface model for \
    the surface mould to be made for")
    parametersFormLayout.addRow("Skin Surface Model ",
                                 self.surfaceModelComboBox)
    
    
    # output model ComboBox (overwritten) - drop down menu
    self.ouputMouldComboBox = slicer.qMRMLNodeComboBox()
    self.ouputMouldComboBox.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.ouputMouldComboBox.renameEnabled = True
    self.ouputMouldComboBox.selectNodeUponCreation = True
    self.ouputMouldComboBox.addEnabled = True
    self.ouputMouldComboBox.removeEnabled = True
    self.ouputMouldComboBox.noneEnabled = False
    self.ouputMouldComboBox.showHidden = False
    self.ouputMouldComboBox.showChildNodeTypes = False
    self.ouputMouldComboBox.setMRMLScene( slicer.mrmlScene )
    self.ouputMouldComboBox.setToolTip( "This model will be overwritten \
    with the output surface mould" )
    parametersFormLayout.addRow("Output Mould Model ",
                                 self.ouputMouldComboBox)
    
    # ROI node comboBox - drop down menu 
    self.roiComboBox = slicer.qMRMLNodeComboBox()
    self.roiComboBox.nodeTypes = ( ("vtkMRMLAnnotationROINode"), "" )
    self.roiComboBox.renameEnabled = True
    self.roiComboBox.selectNodeUponCreation = True
    self.roiComboBox.addEnabled = False
    self.roiComboBox.removeEnabled = True
    self.roiComboBox.noneEnabled = False
    self.roiComboBox.showHidden = False
    self.roiComboBox.showChildNodeTypes = False
    self.roiComboBox.setMRMLScene( slicer.mrmlScene )
    self.roiComboBox.setToolTip("Choose the area of the skin \
    surface that the mould is to be made for. This determines the final size \
    of the mould. ")
    parametersFormLayout.addRow("Region of Interest ",
                                 self.roiComboBox)
    
    # Ruler node comboBox - drop down menu 
    self.rulerComboBox = slicer.qMRMLNodeComboBox()
    self.rulerComboBox.nodeTypes = ( ("vtkMRMLAnnotationRulerNode"), "" )
    self.rulerComboBox.renameEnabled = True
    self.rulerComboBox.selectNodeUponCreation = True
    self.rulerComboBox.addEnabled = False
    self.rulerComboBox.removeEnabled = True
    self.rulerComboBox.noneEnabled = False
    self.rulerComboBox.showHidden = False
    self.rulerComboBox.showChildNodeTypes = False
    self.rulerComboBox.setMRMLScene( slicer.mrmlScene )
    self.rulerComboBox.setToolTip("This ruler and the pairs of points\
    , will be used to define a plane used in path generation")
    parametersFormLayout.addRow("Ruler ",
                                 self.rulerComboBox)
    
    # First catheter start point fiducial selector - drop down menu
    self.startPointComboBox = slicer.qMRMLNodeComboBox()
    self.startPointComboBox.nodeTypes = ( ("vtkMRMLMarkupsFiducialNode"), "" )
    self.startPointComboBox.renameEnabled = True
    self.startPointComboBox.selectNodeUponCreation = True
    self.startPointComboBox.addEnabled = False
    self.startPointComboBox.removeEnabled = True
    self.startPointComboBox.noneEnabled = False
    self.startPointComboBox.showHidden = False
    self.startPointComboBox.showChildNodeTypes = False
    self.startPointComboBox.setMRMLScene( slicer.mrmlScene )
    self.startPointComboBox.setToolTip("Choose the markup list that \
    contains the starting points of the catheter paths")
    parametersFormLayout.addRow("Catheter Start Points ",
                                 self.startPointComboBox)
    
    
    # Second catheter fiducial selector - drop down menu 
    self.endPointComboBox = slicer.qMRMLNodeComboBox()
    self.endPointComboBox.nodeTypes = ( ("vtkMRMLMarkupsFiducialNode"), "" )
    self.endPointComboBox.renameEnabled = True
    self.endPointComboBox.selectNodeUponCreation = True
    self.endPointComboBox.addEnabled = False
    self.endPointComboBox.removeEnabled = True
    self.endPointComboBox.noneEnabled = False
    self.endPointComboBox.showHidden = False
    self.endPointComboBox.showChildNodeTypes = False
    self.endPointComboBox.setMRMLScene( slicer.mrmlScene )
    self.endPointComboBox.setToolTip( """Choose the markup list node that, 
    contains the end points of the catheter paths""" )
    parametersFormLayout.addRow("Catheter End Points ", self.endPointComboBox)
    
    # Minimum catheter distance from target surface - slider and spinbox
    self.minCathDistanceSlider = ctk.ctkSliderWidget()
    self.minCathDistanceSlider.setToolTip(""" The closest absolute distance 
    a catheter is aloud to get to the skin""")
    self.minCathDistanceSlider.minimum = 1.5
    self.minCathDistanceSlider.maximum = 10
    self.minCathDistanceSlider.value = 2
    parametersFormLayout.addRow("Distance from Skin",
                                 self.minCathDistanceSlider)
    
    # Minimum catheter distance from target surface - slider and spinbox
    self.slitThickness = ctk.ctkSliderWidget()
    self.slitThickness.setToolTip(""" The thickness of the slit instantiated
    into the mould.""")
    self.slitThickness.minimum = 0.5
    self.slitThickness.maximum = 10
    self.slitThickness.value = 1.0
    parametersFormLayout.addRow("Slit Thickness (mm)",
                                 self.slitThickness)
    
    
    # Catheter tube radius value - slider and spinbox
    self.cathRadiusSlider = ctk.ctkSliderWidget()
    self.cathRadiusSlider.toolTip = """Defines the radius of the catheter 
    tubes, in mm. Default: 2mm"""
    self.cathRadiusSlider.minimum = 1.5
    self.cathRadiusSlider.maximum = 10
    self.cathRadiusSlider.value = 2
    parametersFormLayout.addRow("Catheter Radius ", self.cathRadiusSlider)
    

    # Catheter path minimum radius of curvature value - slider and spinbox
    self.minCurvatureSlider = ctk.ctkSliderWidget()
    self.minCurvatureSlider.toolTip = "Defines the minimum radius of \
    curvature of any point along the catheter paths, in mm. "
    self.minCurvatureSlider.minimum = 0
    self.minCurvatureSlider.maximum = 60
    self.minCurvatureSlider.value = 5
    parametersFormLayout.addRow("Catheter Curvature ",
                                 self.minCurvatureSlider)
    
    # Output mould model resolution value - slider and spinbox
    self.algorythm = ctk.ctkSliderWidget()
    self.algorythm.toolTip = "How Many Cycles to smooth"
    self.algorythm.minimum = 0
    self.algorythm.maximum = 1000
    self.algorythm.value = 10
    parametersFormLayout.addRow("AlgorythmRunning ",
                                 self.algorythm)
    
    
    # Make Brachytherapy Surface Mould - button
    self.createMouldButton = qt.QPushButton()
    self.createMouldButton.setText("Apply Mould")
    self.createMouldButton.toolTip = "Creates a mask of a specified \
    thickness from the face of interest. Catheter paths are carved out \
    along the line connecting the pairs of fiducials. This overwrites \
    the Output Model."
    self.createMouldButton.enabled = True
    parametersFormLayout.addRow(self.createMouldButton)
    
    
    # Add vertical spacer
    self.layout.addStretch(7)
    
    # connections
    self.createMouldButton.connect('clicked(bool)',self.CreateMould)
    self.createTestObjectButton.connect('clicked(bool)', self.CreateTestObject)
    self.reloadButton.connect('clicked()', self.onReload)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)
    
    # Saves time with loading the module names in
    self.QuickSetup() # Mark Schumacher, added This For convenience 
  def CheckInputs(self):
    # Make an exception for ruler cannot intersect with the skin 
    # (We do this so we can define which side of the surface in the mask side)
    if (self.ouputMouldComboBox.currentNode() ==
          self.surfaceModelComboBox.currentNode()):
      raise Exception ("Error, Surface Output and Input are the same Nodes.")
    if (self.startPointComboBox.currentNode() ==  
          self.endPointComboBox.currentNode()):
      raise Exception ("Error, Fiducial Point mark ups are the same")  
    if (self.startPointComboBox.currentNode().GetNumberOfFiducials() != 
          self.endPointComboBox.currentNode().GetNumberOfFiducials()):
      raise Exception ("Error, number of points not equal")
  def onReload(self,moduleName="HDRMould"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName. """
    
    import imp, sys, os, slicer
    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    print filePath
    
    
    
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)
    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()    
  def onReloadAndTest(self,moduleName="HDRMould"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(), 
          "Reload and Test", 'Exception!\n\n' + str(e) +
          "\n\nSee Python Console for Stack Trace")
  def QuickSetup(self):
    """ Instead of always adding the right models into the form
    during testing we can just make our forms try to autoload
    nodes that we are using for testing
    """
    x=slicer.mrmlScene.GetNodesByName("Model")
    if x.GetNumberOfItems()!=0:
      y=x.GetItemAsObject(0)
      self.ouputMouldComboBox.setCurrentNode(y)
    
    x=slicer.mrmlScene.GetNodesByName("EndPoints")
    if x.GetNumberOfItems()!=0:
      y=x.GetItemAsObject(0)
      self.endPointComboBox.setCurrentNode(y)
      
    x=slicer.mrmlScene.GetNodesByName("StartPoints")
    if x.GetNumberOfItems()!=0:
      y=x.GetItemAsObject(0)
      self.startPointComboBox.setCurrentNode(y)
  def CreateTestObject(self):
    TestObject()
  def CreateMould(self):
    global ALGOO
    ALGOO = self.algorythm.value
    
    """ The "main" of our entire program, Start here.
    This is the Method that gets run upon clicking of the 
    createMouldButton defined in Setup. 
    """
    print("HDRMouldWidget::Apply Mould Button Pressed")
    mouldLogic = MouldLogic(self.startPointComboBox) #number of paths total
    utility = Util_HDR()
    
    print("HDRMouldWidget::CheckInputs()")
    self.CheckInputs()
    
    print("MouldLogic::ClipData()")
    ROI=self.roiComboBox.currentNode() #ROI from widget
    noisySurfacePolyData=self.surfaceModelComboBox.currentNode().GetPolyData()
    clippedFace=mouldLogic.ClipData(ROI, noisySurfacePolyData)
    #clippedFace is the Algorythm Object
    if DEBUG_CLIPPING:
      node=utility.DisplayPolyData("Clipped-Data",mouldLogic.clippedSurface)
      node.EdgeVisibilityOn()
      utility.PolyDataWriter(mouldLogic.minimumDistanceMask,
                             "C:\\MakeHDRApplicatorMask\\doc\\"+\
                             "DebugPolyData\\ClippedData.vtk")
    
    print("MouldLogic::MinimumDistanceMask()")
    distanceFromTubeCenter=self.minCathDistanceSlider.value+self.cathRadiusSlider.value #getting value from widget
    ruler = self.rulerComboBox.currentNode() #unpacking ruler
    connectivityFilter=mouldLogic.MinimumDistanceMask(clippedFace,
                                                    distanceFromTubeCenter, ROI, ruler)
    if DEBUG_MINMASK:
      utility.DisplayPolyData("Minimum-Distance-Mask", mouldLogic.minimumDistanceMask)
      utility.PolyDataWriter(mouldLogic.minimumDistanceMask,
                                "C:\\MakeHDRApplicatorMask\\doc\\"+\
                                "DebugPolyData\\MinMask.vtk")
    
    print("MouldLogic::CreatePlane() -ran for each point pair")
    startPoints=utility.UnpackPoints(self.startPointComboBox.currentNode())#list of points
    endPoints=utility.UnpackPoints(self.endPointComboBox.currentNode())#list of end points
    mouldLogic.CreateMultiplePlanes(startPoints,
                                    endPoints,ruler)# mouldLogic.listOfPlanes init 
    if DEBUG_CUTTINGPLANES:
      mouldLogic.count=0 # Important for naming of the planes in debug
      mouldLogic.DisplayPlanes(mouldLogic.listOfPlanes,ROI)
      
       
    print("MouldLogic::CreateBackLine() -for each plane")
    for implicitPlane in mouldLogic.listOfPlanes:
      mouldLogic.CreateBackLine(ruler, ROI, implicitPlane)
    
    print ("CatheterPath::Initializing")
    for i in range (len(mouldLogic.listOfBackLines)):
      print "CatheterPath::Initializing for Plane" , str(i)
      minCurvature=self.minCurvatureSlider.value # curvature
      catheterPath=CatheterPath(mouldLogic.minimumDistanceMask,
                                mouldLogic.listOfPlanes[i],minCurvature,
                                 str(i), mouldLogic.listOfBackLines[i])
      #Move all of these to a GetTube Function
      mouldLogic.tubes.append(catheterPath.CreateTube(self.cathRadiusSlider.value,ROI))
      slitSize=self.slitThickness.value
      mouldLogic.CreateSlit(mouldLogic.listOfNormals[i],
                            catheterPath.pathPolydata,
                            ruler,ROI,slitSize) #appends to self.slitPlanes
                                                                                                                                                                                                                                                  
    binarizedVolume=utility.createVolumeFromRoi(ROI,0.5) # binarized Volumes contain Image data within them.
    utility.polyDataToImageData(mouldLogic.tubes[0],binarizedVolume)
    
      

#       facePolydata.AddInput(tube)
#       tubePolydata.AddInput(tube) # Add tube to mask
#       maskPolydata=mouldLogic.AddTubeToMask(maskPolydata,tube,ROI,self.cathRadiusSlider.value,ruler)
#       if DEBUG_MINMASK:
#         utility.DisplayPolyData("Minimum-Distance-Mask"+str(i),maskPolydata)
#       
#     print ("MouldLogic::GenerateMould()")
#     distanceFromMask=self.minCathDistanceSlider.value 
#     mouldLogic.GenerateMould(facePolydata,distanceFromMask,ROI, tubePolydata,clippedFace)


class MouldLogic:
  """ Defines the logic for creating the mould
  """
  def __init__(self, numberOfPaths):
    self.count=0 #used for creating unique names in debug
    self.numberOfPaths=numberOfPaths.currentNode().GetNumberOfFiducials() 
    self.utility=Util_HDR() #utility Object with common methods
    self.skinSurface=None # Set after ClipData()
    self.minimumDistanceMask= None # Set after MinimumDistanceMask()
    self.clippedSurface= None # Set after ClipData()
    self.listOfCatheters=[] # Set After CreateRawPath()
    self.listOfPlanes=[] #Implicit Planes , created after CreatePlane()
    self.listOfBackLines=[] # The line created at the back of the Mask
    self.listOfNormals=[]
    self.slitPlanes=[]
    self.tubes=[]
  def ClipData(self, ROI , noisySurfacePolyData):
    """ Returns the clipped polydata from the region defined by the ROI
    Turn on the Debug to make the clipped object appear, 
    For specific filter functionality see DataFlow doc: ClipData.pdf
    """
    connectivityFilter = vtk.vtkPolyDataConnectivityFilter()
    self.utility.PolyDataWriter(noisySurfacePolyData,
                                "C:\\MakeHDRApplicatorMask\\doc\\"+\
                                "DebugPolyData\\PreClipped.vtk")
    connectivityFilter.SetInputData(noisySurfacePolyData)
    connectivityFilter.SetExtractionModeToLargestRegion()
    connectivityFilter.Update()
    self.skinSurface=connectivityFilter.GetOutput()  #skinSurface Set
    # Expansion of ROI is explained in vtkImplicitModeller limitations
    ROIExtents= self.utility.GetROIExtents(ROI)
    BiggerROI=self.utility.ExpandExtents(ROIExtents, .5)
    #See vtkImplicitModdeler limitations.pdf for explanation
    implicitBoxRegion = vtk.vtkBox()
    implicitBoxRegion.SetBounds(BiggerROI)
    
    clipper=vtk.vtkClipPolyData()
    clipper.InsideOutOn() # Clip the regions outside of implicit function
    clipper.SetInputConnection(connectivityFilter.GetOutputPort())
    clipper.SetClipFunction(implicitBoxRegion)
    clipper.Update()
    self.clippedSurface=clipper.GetOutput()
    return clipper
  def CreateMultiplePlanes(self,startPoints,endPoints,ruler):
    """ Gets the inputs ready for input into createPlane()
    this function will return back multiple implicit planes in one list
    """
    rulerDirection=self.utility.GetRulerVector(ruler) 
    for i in range(len(startPoints)):   #create num of planes for each pair
      startPoint = startPoints[i]
      endPoint = endPoints[i]
      self.CreatePlane(startPoint,endPoint,rulerDirection)
  def CreatePlane(self, startPoint, endPoint, direction):
    """ Takes two points and a direction vector
    returns an implicit function defining a plane
    """
    a,b,c=startPoint #quick unpack
    d,e,f=endPoint #quick unpack
    q,r,s=a-d,b-e,c-f #quick direction vector
    catheterDirection=[q,r,s]
    normal = self.utility.CrossProduct(direction, catheterDirection)
    self.listOfNormals.append(normal)
    implicitPlane= vtk.vtkPlane()
    implicitPlane.SetNormal(normal)
    implicitPlane.SetOrigin(startPoint)
    self.listOfPlanes.append(implicitPlane) # Saving plane objects onto object
  def DisplayPlanes(self,listOfPlanes,ROI):
    """ This function is preparation before sending into the more
    general function DisplayImplicit()
    Note, any changing of the color of display of the planes is 
    done so here. 
    """
    for index in range(len(listOfPlanes)):
      name="Plane-"+str(self.count) #To Create Unique Name Required
      self.count+=1 # Increment the unique name for the plane
      node=self.utility.DisplayImplicit(name, listOfPlanes[index],ROI)
      node.SetColor(1,0,0) #Red ...Max 1 for each column
      node.SetOpacity(0.4)
  def MinimumDistanceMask(self, vtkAlgorythmObject, distanceFromMask, ROI, ruler):
    """ Takes an algorythm object which is will send through a pipeline to 
    create a mask defining the minimum distance value from the skin surface
    returns an algorythm object as well to preform GetOutput() -> polydata
    or GetOutputPort() -> algorythm
    see MinimumDistanceMask.pdf 
    """
    if distanceFromMask<2:
      print "WARNING: MouldLogic: MinimumDistanceMask implicit",
      "modeling is very unstable below 1.5 , mask may degrade",
      "and lines will become discontinuous."
    Extents=self.utility.GetROIExtents(ROI)
    implicitModeller = vtk.vtkImplicitModeller()
    implicitModeller.SetInputConnection(vtkAlgorythmObject.GetOutputPort())
    implicitModeller.SetMaximumDistance(distanceFromMask)
    implicitModeller.SetModelBounds(Extents)
    implicitModeller.AdjustBoundsOn()
    implicitModeller.SetAdjustBounds(10) # Removes the boundary effects
    implicitModeller.CappingOff()# Important to create disjoint inner and outer masks
    implicitModeller.SetProcessModeToPerVoxel()
    implicitModeller.Update()
    
    contourFilter = vtk.vtkContourFilter()
    contourFilter.SetValue(0, distanceFromMask)
    contourFilter.SetInputConnection(implicitModeller.GetOutputPort())
    contourFilter.Update()  
    
    normalsFunction = vtk.vtkPolyDataNormals()
    normalsFunction.FlipNormalsOn ()
    normalsFunction.AddInputConnection(contourFilter.GetOutputPort())
    normalsFunction.Update()
    
    implicitBoxRegion = vtk.vtkBox()
    implicitBoxRegion.SetBounds(Extents)
    clipper2=vtk.vtkClipPolyData()
    clipper2.InsideOutOn() # Clip the regions outside of implicit function
    clipper2.SetInputConnection(normalsFunction.GetOutputPort())
    clipper2.SetClipFunction(implicitBoxRegion)
    clipper2.Update()
    
    closestPoint=[0,0,0]
    ruler.GetPosition1(closestPoint)
    connectivityFilter = vtk.vtkPolyDataConnectivityFilter()
    connectivityFilter.SetInputConnection(clipper2.GetOutputPort())
    connectivityFilter.SetExtractionModeToClosestPointRegion()
    connectivityFilter.SetClosestPoint(closestPoint)
    connectivityFilter.Update()
    
    self.minimumDistanceMask=connectivityFilter.GetOutput()
    return connectivityFilter
  def CreateBackLine(self,ruler,ROI,implicitPlane):
    """ Creates the polydata for where the cutting plane hits the the back
    of the ROI.  
    This backline will be used to close the catheter path allowing for the
    specification of Towards or Away from the face
    
    ASSERTION: that the ruler's second point will be closest to the 
    front of our mask. 
    """
    roiPoints=self.utility.GetROIPoints(ROI)
    frontExtentIndex=self.utility.GetClosestExtent(ruler,ROI)
    backExtentIndex=self.utility.GetOppositeExtent(frontExtentIndex)
    
    #Creating an implict plane for the back of the ROI
    ROICenterPoint = [0,0,0]
    ROI.GetXYZ(ROICenterPoint)
    backNormal=self.utility.GetVector(ROICenterPoint, roiPoints[backExtentIndex])
    backPlane= vtk.vtkPlane()
    backPlane.SetNormal(backNormal)
    backPlane.SetOrigin(roiPoints[backExtentIndex])
    
    #Finding the Intercept of this and the CuttingPlane
    sampleFunction=vtk.vtkSampleFunction()
    sampleFunction.SetSampleDimensions(10,10,10)
    sampleFunction.SetImplicitFunction(backPlane)
    bounds=self.utility.ExpandExtents(self.utility.GetROIExtents(ROI),1)
    sampleFunction.SetModelBounds(bounds)
    sampleFunction.Update()
    
    contourFilter=vtk.vtkContourFilter()
    contourFilter.SetInputConnection(sampleFunction.GetOutputPort())
    contourFilter.GenerateValues(1,1,1)
    contourFilter.Update()
    
    cutter=vtk.vtkCutter()
    cutter.SetInputConnection(contourFilter.GetOutputPort())
    cutter.SetCutFunction(implicitPlane)
    cutter.GenerateValues(1,1,1)
    cutter.Update()
    self.listOfBackLines.append(cutter.GetOutput())
    PATH= ROOTPATH+"\\doc\\DebugPolyData\\"+"BackLine-"+str(len(self.listOfBackLines))
    self.utility.PolyDataWriter(self.listOfBackLines[-1],PATH+".vtk")
  def AddTubeToMask(self,maskPolydata,tube,ROI,radius,ruler):
    ROIExtents=self.utility.GetROIExtents(ROI)
    implicitFilter = vtk.vtkImplicitModeller()
    implicitFilter.SetInput(tube)
    implicitFilter.SetSampleDimensions(70,70,70)
    implicitFilter.SetMaximumDistance(radius)
    implicitFilter.SetModelBounds(ROIExtents)
    implicitFilter.SetProcessModeToPerVoxel()
    contourFilter = vtk.vtkContourFilter()
    contourFilter.SetValue(0, radius)
    implicitFilter.AdjustBoundsOn()
    implicitFilter.SetAdjustBounds(1) # Removes the boundary effects
    implicitFilter.CappingOff()
    contourFilter.SetInputConnection(implicitFilter.GetOutputPort())
    normalsFunction = vtk.vtkPolyDataNormals()
    normalsFunction.AutoOrientNormalsOn()
    normalsFunction.AddInputConnection(contourFilter.GetOutputPort())
    
    unionFilter = vtk.vtkBooleanOperationPolyDataFilter()
    unionFilter.SetOperationToUnion()
    unionFilter.SetInput(0, normalsFunction.GetOutput())
    unionFilter.SetInput(1, maskPolydata)
    return unionFilter.GetOutput()
  def GenerateMould(self,facePolydata,distanceFromMask,ROI,tubePolydata,clippedFace):
    ROIExtents=self.utility.GetROIExtents(ROI)
    outerFaceImplicitFunction = vtk.vtkImplicitModeller()
    outerFaceImplicitFunction.SetInputConnection(facePolydata.GetOutputPort())
    outerFaceImplicitFunction.SetSampleDimensions(70,70,70)
    outerFaceImplicitFunction.SetMaximumDistance(distanceFromMask)
    outerFaceImplicitFunction.SetModelBounds(ROIExtents)
    outerFaceImplicitFunction.SetProcessModeToPerVoxel()
    outerMaskContourFunction = vtk.vtkContourFilter()
    #TODO Find out the the allowed thinkness of the plastic
    THICKNESS=3
    outerMaskContourFunction.SetValue(0, THICKNESS)
    outerMaskContourFunction.SetInputConnection(outerFaceImplicitFunction.GetOutputPort())  
    
    outerFaceNormalsFunction = vtk.vtkPolyDataNormals()
    outerFaceNormalsFunction.AutoOrientNormalsOn()
    outerFaceNormalsFunction.AddInputConnection(outerMaskContourFunction.GetOutputPort())
    # Subtract the Tubes from the mask 
    subtractionFilter1 = vtk.vtkBooleanOperationPolyDataFilter()
    subtractionFilter1.SetOperationToDifference()
    subtractionFilter1.SetInputConnection(0, outerFaceNormalsFunction.GetOutputPort())
    subtractionFilter1.SetInputConnection(1, tubePolydata.GetOutputPort())
    # Subtract the inner face from the outer face to make the mask
    subtractionFilter2 = vtk.vtkBooleanOperationPolyDataFilter()
    subtractionFilter2.SetOperationToDifference()
    subtractionFilter2.SetInputConnection(0, subtractionFilter1.GetOutputPort())
    subtractionFilter2.SetInputConnection(1, clippedFace.GetOutputPort())
    x=self.utility.DisplayPolyData("Mask", subtractionFilter2.GetOutput())
    x.SetColor(0.8,0.8,0.8)
    x.SetOpacity(1)
  def CreateSlit(self,normal,pathPolydata,ruler,ROI,slitSize):
    """ Here we are going to create a boxSource , the size of the 2*ROI in the X,Y
    and the size of the slit Size in the Z. 
    We are then going to translate the box source to its correct location in slicer
    As always to visualize , a DEBUG option can be set at the top.
    x is L->R, y is P->A, z is I->S
    """ 
    #Cube Creation
    roiPoints=self.utility.GetROIPoints(ROI)
    frontExtentIndex=self.utility.GetClosestExtent(ruler,ROI)
    backExtentIndex=self.utility.GetOppositeExtent(frontExtentIndex)
    pointA=numpy.array(roiPoints[frontExtentIndex])
    pointB=numpy.array(roiPoints[backExtentIndex])
    yDist = numpy.linalg.norm(pointA-pointB)
    numPoints=pathPolydata.GetNumberOfPoints()
    pointA=numpy.array(pathPolydata.GetPoint(0))
    pointB=numpy.array(pathPolydata.GetPoint(numPoints-1))
    xDist = numpy.linalg.norm(pointA-pointB)
    zDist=slitSize #Rewording the parameter to make it easier to understand
    slitCube=vtk.vtkCubeSource()
    slitCube.SetBounds(0,xDist,-yDist,yDist,-zDist/2,zDist/2)# (Xmin, Xmax, Ymin, Ymax,Zmin, Zmax)
    
    #Transforming Cube
    transformFilter=vtk.vtkTransformFilter()
    transform=vtk.vtkTransform()
    matrix=vtk.vtkMatrix4x4()
    pointA=numpy.array(pathPolydata.GetPoint(0))
    pointB=numpy.array(pathPolydata.GetPoint(numPoints-1))
    xVector=pointA-pointB
    xDist = numpy.linalg.norm(pointA-pointB)
    xUnitVector=(xVector[0]/xDist,xVector[1]/xDist,xVector[2]/xDist)
    
    yVector=self.utility.GetRulerVector(ruler)
    yDist=numpy.linalg.norm(yVector)
    yUnitVector=(yVector[0]/yDist,yVector[1]/yDist,yVector[2]/yDist)
    
    zVector=numpy.cross(xVector,yVector)
    zDist=numpy.linalg.norm(zVector)
    zUnitVector= (zVector[0]/zDist,zVector[1]/zDist,zVector[2]/zDist)
    
    origin=pointA=numpy.array(pathPolydata.GetPoint(numPoints-1))
    
    matrix.DeepCopy((xUnitVector[0], yUnitVector[0], zUnitVector[0], origin[0],
                     xUnitVector[1], yUnitVector[1], zUnitVector[1], origin[1],
                     xUnitVector[2], yUnitVector[2], zUnitVector[2], origin[2],
                     0, 0, 0, 1))
    
    transform.SetMatrix(matrix)
    transformFilter.SetTransform(transform)
    transformFilter.SetInputConnection(slitCube.GetOutputPort())
    transformFilter.Update()
    self.slitPlanes.append(transformFilter.GetOutput())
    if len(self.slitPlanes)==self.numberOfPaths and DEBUG_SLITPLANES==True:
      for i in range (self.numberOfPaths):
        self.utility.DisplayPolyData("Slit"+str(i), self.slitPlanes[i])
    return transformFilter.GetOutput()

class HDRMouldTest():
  """ScriptedLoadableModuleTemplateTest is a subclass of a standard python
  unittest TestCase. Note that this class responds specially to methods
  whose names start with the string "test", so follow the pattern of the
  template when adding test functionality."""
  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()
  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene
    clear will be enough."""
    slicer.mrmlScene.Clear(0)
  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test1_HDRMould()
  def test1_HDRMould(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """
    self.delayDisplay('Test passed!')

class TestObject:
  def SetGlobalParameters(self,ROI,normal,distanceBetweenTubes,maskThickness):
    """Only Set These Once"""
    self.utility=Util_HDR()
    self.distanceBetweenTubes=distanceBetweenTubes
    self.maskThickness=maskThickness
    self.ROIExtents=ROI
    self.normal=normal
    self.bottomPlane=self.CreateBottomPlane()
    self.PATH= ROOTPATH+"\\doc\\DebugPolyData\\"
    self.TUBENUMBER=0
    self.tubeList=[]
    self.planeList=[]
    self.combinedTubePlane=[]
    self.tubes=[]
    self.currentY=0
  def SetLocalParameters(self,minimumCurvature,tubeRadius,planeWidth):
    self.tubeRadius=tubeRadius
    self.lengthPath=70
    self.startPoint=[0,self.currentY,0]
    self.currentY+=(self.tubeRadius)+self.distanceBetweenTubes+2
    self.minimumCurvature=minimumCurvature
    self.planeWidth=planeWidth
    #self.circleInfo=(center1,center2,center3)
    self.circleInfo=self.CreateCircles(self.startPoint, self.minimumCurvature)
    self.path=self.CreatePath()
    self.planeList.append(self.OpeningPlane())
    self.tubes.append(self.CreateTubes())

  def __init__(self):
    """ROI, Normal, Distance between tubes mm ,maskthickness"""
    self.SetGlobalParameters([0,70,-5,50,-5,50],(0,0,1),8,3)
    
    """(self.minimumCurvature, self.tubeRadius, planeWidth)"""
    #Catheter Radius = 1.0
    self.SetLocalParameters(10, 1.0, 1.0)
    self.SetLocalParameters(12, 1.0, 1.0)
    self.SetLocalParameters(14, 1.0, 1.0)
    self.SetLocalParameters(16, 1.0, 1.0)
    
    #Catheter Radius = 1.25
    self.SetLocalParameters(10, 1.333, 1.0)
    self.SetLocalParameters(12, 1.333, 1.0)
    self.SetLocalParameters(14, 1.333, 1.0)
    self.SetLocalParameters(16, 1.333, 1.0)
     
    #Catheter Radius = 1.5
    self.SetLocalParameters(10, 1.667, 1.5)
    self.SetLocalParameters(12, 1.667, 1.5)
    self.SetLocalParameters(14, 1.667, 1.5)
    self.SetLocalParameters(16, 1.667, 1.5)
    
    appendedPolydata=vtk.vtkAppendPolyData()
    i=0
    for item in self.tubes:
      i+=1
      appendedPolydata.AddInputConnection(item.GetOutputPort())
      #self.utility.DisplayPolyData("tube"+str(i), item.GetOutput())
    self.utility.DisplayPolyData("wholeMask", appendedPolydata.GetOutput())
    
#     boxFunction=vtk.vtkBox()
#     boxFunction.SetBounds([-10,70,-10,50,-100,100])
#     clippingFilter=vtk.vtkCutter()
#     clippingFilter.SetInputConnection(appendedPolydata.GetOutputPort())
#     clippingFilter.SetCutFunction(boxFunction)
#     clippingFilter.SetValue(0,0)
#     self.utility.DisplayPolyData("clippedWholeMask", clippingFilter.GetOutput())
    
    return
  def ExtendPath(self):
    numberOfPoints=self.path.GetNumberOfPoints()+2
    points=self.path.GetPoints()
    newPoints=vtk.vtkPoints()
    newPoints.SetNumberOfPoints(numberOfPoints)
    newPoints.SetPoint(0,-10,self.circleInfo[0][1],0)
    for i in range (self.path.GetNumberOfPoints()):
      newPoints.SetPoint(i+1,points.GetPoint(i))
    newPoints.SetPoint(numberOfPoints-1,self.lengthPath+5,self.circleInfo[0][1],0)
    
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(numberOfPoints)
    for i in range (numberOfPoints):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPd=vtk.vtkPolyData()
    newPd.SetPoints(newPoints)
    newPd.SetLines(cellArray)
    
    spline = vtk.vtkKochanekSpline()
    splineFilter = vtk.vtkSplineFilter()
    splineFilter.SetInput(newPd)
    splineFilter.SetSubdivideToLength()
    NUMBER_OF_MM_BETWEEN_POINTS=1
    splineFilter.SetLength(NUMBER_OF_MM_BETWEEN_POINTS)
    splineFilter.SetSpline(spline)
    splineFilter.Update()
    return splineFilter.GetOutput()
  def CreateTubes(self):
    """Creates the tubes that hold the catheters."""
    
    extendedPath=self.ExtendPath()
    cathNormals=vtk.vtkPolyDataNormals()
    cathNormals.SetInput(extendedPath)
    cathNormals.AutoOrientNormalsOn()
    catheterHole=vtk.vtkTubeFilter()
    catheterHole.CappingOn()
    catheterHole.SetInput(cathNormals.GetOutput())
    catheterHole.SetNumberOfSides(100)
    catheterHole.SetRadius(self.tubeRadius)
    cathNormals=vtk.vtkPolyDataNormals()
    cathNormals.FlipNormalsOn()
    cathNormals.SetInputConnection(catheterHole.GetOutputPort())
    self.utility.DisplayPolyData("cathNormals", cathNormals.GetOutput())
    
    tube=vtk.vtkTubeFilter()
    tube.CappingOn()
    tube.SetInput(self.path)
    tube.SetNumberOfSides(100)
    tube.SetRadius(self.distanceBetweenTubes)
    tube.UseDefaultNormalOn()
    tubeNormals=vtk.vtkPolyDataNormals()
    tubeNormals.SetInputConnection(tube.GetOutputPort())
    self.utility.DisplayPolyData("tubeNormals", tubeNormals.GetOutput())
    
    HEIGHT=50
    cube = vtk.vtkCubeSource()
    cube.SetXLength(self.lengthPath+20)
    cube.SetYLength(self.planeWidth)
    cube.SetZLength(HEIGHT)
    cube.SetCenter(self.lengthPath/2,self.circleInfo[0][1],0+HEIGHT/2)
    cutTriangles=vtk.vtkTriangleFilter()
    cutTriangles.SetInputConnection(cube.GetOutputPort())
    cubeNormals=vtk.vtkPolyDataNormals()
    cubeNormals.AutoOrientNormalsOn()
    cubeNormals.SetInputConnection(cutTriangles.GetOutputPort())
    cubeTubeDifference=vtk.vtkBooleanOperationPolyDataFilter()
    cubeTubeDifference.SetOperationToDifference()
    cubeTubeDifference.SetInputConnection(0,tubeNormals.GetOutputPort())
    cubeTubeDifference.SetInputConnection(1,cubeNormals.GetOutputPort())
    self.utility.DisplayPolyData("Removed", cubeTubeDifference.GetOutput())
    
    cathAndCutTubeDiff=vtk.vtkBooleanOperationPolyDataFilter()
    cathAndCutTubeDiff.SetOperationToIntersection()
    cathAndCutTubeDiff.SetInputConnection(0,cubeTubeDifference.GetOutputPort())
    cathAndCutTubeDiff.SetInputConnection(1,cathNormals.GetOutputPort())
    #self.utility.DisplayPolyData("Second", cathAndCutTubeDiff.GetOutput())
    return cathAndCutTubeDiff
  def ShiftPathUp(self,path,mmAmount):
    points=path.GetPoints()
    newPoints=vtk.vtkPoints()
    newPoints.SetNumberOfPoints(points.GetNumberOfPoints())
    for i in range (path.GetNumberOfPoints()):
      newPoints.SetPoint(i,points.GetPoint(i)[0],points.GetPoint(i)[1],points.GetPoint(i)[2]+mmAmount)
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(points.GetNumberOfPoints())
    for i in range (points.GetNumberOfPoints()):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPd=vtk.vtkPolyData()
    newPd.SetPoints(newPoints)
    newPd.SetLines(cellArray)
    return newPd
  def GenerateFinalMask(self):
    unionOfTubes=vtk.vtkBooleanOperationPolyDataFilter()
    unionOfTubes.SetOperationToUnion()
    i=0
    for item in self.tubes:
      unionOfTubes.SetInputConnection(i,item.GetOutputPort())
      i+=1
    return unionOfTubes.GetOutput()
    
  def Combine(self):
    subtractionFilter1=vtk.vtkBooleanOperationPolyDataFilter()
    subtractionFilter1.SetOperationToDifference()
    subtractionFilter1.SetInput(self.tubeList[-1])
    subtractionFilter1.SetInput(self.planeList[-1])
    return subtractionFilter1.GetOutput()
  def OpeningPlane(self):
    cube = vtk.vtkCubeSource()
    cube.SetBounds(self.startPoint[0]+5,self.ROIExtents[1]-5, # L,R
                   self.startPoint[1]-self.planeWidth,self.startPoint[1]+self.planeWidth, #A,P
                   self.startPoint[2]+self.tubeRadius,self.ROIExtents[5]) #I,S
    return cube
  def CreatePath(self, pointsPerQuarterRotation=90):
    pointsPerCircle=pointsPerQuarterRotation*4+1 #EndPoint
    points=vtk.vtkPoints()
    points.SetNumberOfPoints(pointsPerCircle)
    Ycomp=self.circleInfo[0][1] # never changes
    while pointsPerQuarterRotation!=0:
      oppositeSide=self.minimumCurvature*numpy.sin(numpy.radians(90-pointsPerQuarterRotation))
      adjacentSide=self.minimumCurvature*numpy.cos(numpy.radians(90-pointsPerQuarterRotation))
      #First Quarter Rotation
      indexFirstRotation=90-pointsPerQuarterRotation
      indexSecondRotation=indexFirstRotation+90
      indexThirdRotation=indexSecondRotation+90
      indexForthRotation=indexThirdRotation+90
      
      points.InsertPoint(indexFirstRotation,
                         oppositeSide,
                         Ycomp,
                         self.minimumCurvature-adjacentSide)
      
      points.InsertPoint(indexSecondRotation,
                         self.minimumCurvature*2-adjacentSide, 
                         Ycomp,
                         oppositeSide+self.minimumCurvature)
      
      points.InsertPoint(indexThirdRotation,
                         2*self.minimumCurvature+oppositeSide,
                         Ycomp,
                         self.minimumCurvature+adjacentSide)
      
      points.InsertPoint(indexForthRotation,
                         self.minimumCurvature*4-adjacentSide,
                         Ycomp,
                         self.minimumCurvature-oppositeSide)
      pointsPerQuarterRotation-=1
      
    points.InsertPoint(360,self.lengthPath,Ycomp,0)
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(361)
    for i in range (361):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPolyData=vtk.vtkPolyData()
    newPolyData.SetPoints(points)
    newPolyData.SetLines(cellArray)
    
    
    
    spline = vtk.vtkKochanekSpline()
    splineFilter = vtk.vtkSplineFilter()
    splineFilter.SetInput(newPolyData)
    splineFilter.SetSubdivideToLength()
    NUMBER_OF_MM_BETWEEN_POINTS=1
    splineFilter.SetLength(NUMBER_OF_MM_BETWEEN_POINTS)
    splineFilter.SetSpline(spline)
    splineFilter.Update()
    return splineFilter.GetOutput()
  def CreateBottomPlane(self):
    implicitPlane= vtk.vtkPlane()
    implicitPlane.SetNormal(self.normal)
    implicitPlane.SetOrigin(0,0,0)
    return implicitPlane
    #self.utility.DisplayImplicit("BottomPlane", self.bottomPlane)
  def CreateCircles(self,startPoint,radius):
    a,b,c=startPoint
    center1=a,b,c+radius # X= Path-lengthwise, Y=between tubes Z=vertically 
    center2=a+2*radius,b,c+radius # for making the circles
    center3=a+4*radius,b,c+radius
    return (center1,center2,center3)

class CatheterPath:
  """ This class only owns a minimum distance mask and an
  implicit plane
  Generation of the path is done step wise so that If Debug is on
  we can analyze the output of each individual step
  """
  def __init__(self, minimumDistanceMask, implicitPlane, minCurvature , ID, backLine):
    self.utility=Util_HDR()
    self.minimumDistanceMask=minimumDistanceMask #vtkPolyData
    self.implicitPlane=implicitPlane #VtkPlane
    self.ID=ID
    self.minCurvature=minCurvature # min catheter radius allowed by the catheter
    self.SetName("backLine"+self.ID) #For Debugging
    self.backLine=self._ConnectPath(backLine) #Backlines are still used for testing point inside
    self.SetName("path"+self.ID) #For Debugging
    self.pathPolydata=self.GenerateRawPath(minimumDistanceMask,implicitPlane)
    self.orderedPtIDs=[] # after ConnectPath()
    self.XArea=self.XArea() # Requires backlines, used in Test point inside and move points out 
    self.unitVectors=[]
    self.SplinePath()
    self.SmoothPath()
    self.length=0 #Set after GenerateRawPath, length of the line
  def SetName(self,name):
    self.name= name
  def GenerateRawPath(self,minimumDistanceMask,implicitPlane):
    """ Cuts the path with the plane 
    the .GetOutput of a cutter will return many lines that contain 2 points 
    We will feed this output into Connect path which will return our
    polydata in managable state --> see connectPath() desciption
    
    Returns polydata with points and connections ordered by index
    """
    cutterFilter = vtk.vtkCutter()
    cutterFilter.SetInputData(minimumDistanceMask)
    cutterFilter.SetCutFunction(implicitPlane)
    cutterFilter.GenerateValues(1, 0.0, 0.0)
    cutterFilter.Update()
    unconnectedPolydata=cutterFilter.GetOutput()
    path= PATHDEBUG + "RawPath-"+self.name + ".vtk"
    self.utility.PolyDataWriter(unconnectedPolydata, path) #creates .vtk File
    if CATHETER_DEBUG_RAW_POINTS: # Very Time Consuming 1-2 seconds to Generate each path
      self.utility.DisplayPoints(unconnectedPolydata,"RawPoints-"+self.name)
    if CATHETER_DEBUG_RAW_PATH:
      self.utility.DisplayPolyData("RawPath-"+self.name, unconnectedPolydata)
    # Before we return we will condense the path into a single Line with that has
    # its points in order with our own made ConnectPath function.
    connectedPolyData=self._ConnectPath(unconnectedPolydata)
    return connectedPolyData
  def _ConnectPath(self,unconnectedPolydata):
    """ condenses the multiple lines (unconnectedPolyData) that are in a 2 point
    per line structure into a single line (connected PolyData). Basically this
    will only work on the output of the vtk.Cutter , which returns output in 
    the 2point per line structure. 
    NORMALLY - the function vtk.stripper() could do this but, that function
    was generating multiple lines , which didn't help.
    """
    lines=unconnectedPolydata.GetLines() #Made up of (PtId1, PtId2) for all connections
    numberOfLines=unconnectedPolydata.GetNumberOfLines() #Number of Lines to check
    numberOfPoints=unconnectedPolydata.GetNumberOfPoints() #Should be just numberOfLines+1
    adjacencyList=[[] for x in xrange(numberOfPoints)] #Empty adjacency list
    # index is Point ID value and the list at that index are the point's neighbors
    
    """Create Adjacency Lists O(n)"""
    lines.InitTraversal()
    for i in range (numberOfLines):
      singleLine=vtk.vtkIdList() # Container for the two IDs
      failSafe=lines.GetNextCell(singleLine) # fills the container 
      if failSafe==0: #This should never run number (lines!=cells)?!
        raise Exception("Error, GetNextCell Failed try looking at polyData output")
      pt1=singleLine.GetId(0)
      pt2=singleLine.GetId(1)
      adjacencyList[pt1].append(int(pt2)) #add a neighbor at pt1 
      adjacencyList[pt2].append(int(pt1)) #add a neighbor to pt2
      
    """ Connecting between the points Order(n) , only using append= O(1)"""
    if len(adjacencyList[0]) == 0:
      raise Exception("Error No points in the Line")
    
    """Connecting Left Side -Arbitrarily chosen to be left"""
    previousIndex=0 #PtID to start with
    leftList=self._GetLeftPath(adjacencyList, adjacencyList[0][0], previousIndex)
    leftList.append(0)
    if len(adjacencyList[0]) == 1: # When 0 is an endpoint
      if len(leftList)!=numberOfPoints: #Must be True unless line breaks
        raise Exception("The Path is not continuous") #Termination and no return
      orderedPtIDs=leftList
      newPolydata=self._ReconstructPolyData(orderedPtIDs,unconnectedPolydata)
      return newPolydata #early return    case when 0 is an endPoint
    
    
    """Connecting Right Side 0 is not an endPoint"""
    previousIndex=0 
    index=adjacencyList[0][1]
    failSafe=0 # used to stop infinite recursion
    while index!=-1: #This is the signal I used from _GetRightPath to signal end
      failSafe+=1
      if (failSafe>numberOfPoints+1):
        raise Exception("The Line may have a cyclic connection")
      leftList.append(index)
      (index,previousIndex)=self._GetRightPath(adjacencyList,index,previousIndex)
    
    if len(leftList)!=numberOfPoints: #Must be True unless line breaks
      raise Exception("The Path is not continuous") #Termination and no return
    orderedPtIDs=leftList
    newPolydata=self._ReconstructPolyData(orderedPtIDs,unconnectedPolydata)
    return newPolydata #second return    case when 0 is not an endPoint
  def _GetRightPath(self, adjacencyList, index, previousIndex):
    """ Not recursive like leftPath but a step through function that
    keeps moving through the list until end is found
    WARNING: Infinite recursion if the line is Connected
    so make sure a failsafe is used"""
    if len(adjacencyList[index]) == 1:
      index= -1
    elif adjacencyList[index][0] != previousIndex:
      previousIndex=index
      index=adjacencyList[index][0]
    else:
      previousIndex=index # need to set previous before overwrite or infinate looping
      index=adjacencyList[index][1]
    return (index,previousIndex)
  def _GetLeftPath(self,adjacencyList, index, previousIndex):
    """ Recursive function that ensures that only appends are made
    Append is an O(1)operation on lists"""
    if len(adjacencyList[index])==3:
      raise Exception("3 Points in adjacency list - Therefore cyclic graph")
    if len(adjacencyList[index])==1:
      return [index]      # This is the endpoint , thus start of our list
    if adjacencyList[index][0]==previousIndex:
      leftList=self._GetLeftPath(adjacencyList,adjacencyList[index][1], index)
    else:
      leftList=self._GetLeftPath(adjacencyList,adjacencyList[index][0], index)
    leftList.append(index)
    return leftList
  def _ReconstructPolyData(self,orderedPtIDs,unconnectedPolydata):
    """ Creates new polyData Points
    Will construct the points so that the endpoints are at 0 and len-1
    """
    newPolyData=vtk.vtkPolyData()
    newPoints=vtk.vtkPoints()
    newPoints.SetNumberOfPoints(unconnectedPolydata.GetNumberOfPoints())
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    idList=vtk.vtkIdList() #container for PtIDS used in Cells to define polyLine
    idList.SetNumberOfIds(unconnectedPolydata.GetNumberOfPoints())
    
    for i in range (len(orderedPtIDs)):
      idList.SetId(i,i)
      newPoints.SetPoint(i,unconnectedPolydata.GetPoint(orderedPtIDs[i]))
    
    cellArray.InsertNextCell(idList) # The cellID will be 0 
    newPolyData.SetPoints(newPoints)
    newPolyData.SetLines(cellArray)
    path= PATHDEBUG + "ReconstructedPath-"+self.name + ".vtk"
    self.utility.PolyDataWriter(newPolyData, path)
    if CATHETER_DEBUG_RECONSTRUCT:
      self.utility.DisplayPolyData("ReconstructedPath-"+self.name, newPolyData)
    return newPolyData
  def SplinePath(self):
    """ This will reconstruct both the polydata and the oreredPtIDs"""
    spline = vtk.vtkKochanekSpline()
    splineFilter = vtk.vtkSplineFilter()
    splineFilter.SetInputData(self.pathPolydata)
    splineFilter.SetSubdivideToLength()
    NUMBER_OF_MM_BETWEEN_POINTS=3
    splineFilter.SetLength(NUMBER_OF_MM_BETWEEN_POINTS)
    splineFilter.SetSpline(spline)
    splineFilter.Update()
    
    self.pathPolydata=splineFilter.GetOutput()
    self.orderedPtIDs=self._GetOrderAfterSpline()
    
    if CATHETER_DEBUG_SPLINE:
      path= PATHDEBUG + "SplinePath-"+self.name + ".vtk"
      self.utility.PolyDataWriter(self.pathPolydata, path)
      a=self.utility.DisplayPolyData("SplinePath-"+self.name, self.pathPolydata)
      a.SetColor(0.5,0,0)
      a.SetLineWidth(5)
      n=self.utility.DisplayPoints(self.pathPolydata, "SplinePoints-"+self.name)
      n.SetColor(0.5,0.5,0)
    return
  def _GetOrderAfterSpline(self):
    """ Only called after a spline , normally splines have lines that are in order 
    but this is just to make sure of it"""
    numberOfPoints=self.pathPolydata.GetNumberOfPoints()
    lines=self.pathPolydata.GetLines()
    lines.InitTraversal() # VTK functions for unwrapping lines 
    singleLine=vtk.vtkIdList() # Container for the Point IDS
    failSafe=lines.GetNextCell(singleLine) # fills the container 
    if failSafe==0: #This should never run number (lines!=cells)?!
      raise Exception("Error, GetNextCell Failed try looking at polyData output")
    numOfIds=singleLine.GetNumberOfIds()
    if numOfIds!=numberOfPoints:
      #Should never happen
      raise Exception("Spline filter not generating a Connected Path")
    orderOfPoints=[]
    for i in range (numOfIds):
      orderOfPoints.append(int(singleLine.GetId(i)))
    if numOfIds!=len(orderOfPoints):
      #Should never happen
      raise Exception("Number of Id's not equal to the list of ordered pts")
    return orderOfPoints
  def SmoothPath(self):
    DISTANCETOMOVEPOINTS=.1 #distance in mm
    self.MovePointsOut(DISTANCETOMOVEPOINTS) 
    self.TestPointInside()
    self.IdentifyBadPoints()
#     for i in range (int(ALGOO)):
#       self.ExpandCurvature()
    self.JacobSmoothing()
    self.SplinePath()
    if CATHETER_DEBUG_SMOOTHEDPATH:
      path= PATHDEBUG + "SmoothedPath-"+self.name + ".vtk"
      self.utility.PolyDataWriter(self.pathPolydata, path)
      x=self.utility.DisplayPolyData("Smoothed-"+self.name, self.pathPolydata)
      x.SetColor(0.5,1,0)
      x.SetAmbient(1)
      x.SetLineWidth(4)
      self.utility.DisplayPoints(self.pathPolydata, "SmoothedPoints-"+self.name)    
#     self.IdentifyBadPoints()
    return
  def MovePointsOut(self, distance):
    """ Moves the Points outwards by @distance(mm) and calculates the unit vectors 
    (facing outwards) for each point 
    """
    cellLocator=vtk.vtkCellLocator()
    cellLocator.SetDataSet(self.XArea)
    cellLocator.LazyEvaluationOn()
    testPolydata=vtk.vtkPolyData()
    testPolydata.DeepCopy(self.pathPolydata) # Might not be needed but to avoid any complications
    modifiedPoints=testPolydata.GetPoints()
    self.unitVectors.append(numpy.array([0,0,0])) #Start Point is not calculated
    # 
    for i in range (1,testPolydata.GetNumberOfPoints() -1 ): # Avoid end points
      (centerPoint,R)=self.GetCenterAndCurvature(i) #Getting CenterPoint and Radius of curvature
      NUMBEROFMM=distance   #length of the Unit vector in millimeters
      pointOnCatheter=numpy.array(self.pathPolydata.GetPoint(i))
      unitVector = (centerPoint-pointOnCatheter)/ (numpy.linalg.norm(centerPoint-pointOnCatheter))*NUMBEROFMM
      
      
      Switch=True # This allows us to alternate between +/- unitVectors, so arrive at the closest side
      x,y,z=self.pathPolydata.GetPoint(i)
      OriginalPoint=x,y,z
      modifiedPoint=testPolydata.GetPoint(i)
      multiplier=0 #increments the unit Vector by another .01mm
      while True: # still inside polygon
        if Switch==True:
          Switch=False 
          multiplier+=1 # increment only every other loop
          x,y,z=OriginalPoint # Deep Copy , no Aliasing
          x = x+ multiplier*unitVector[0]
          y = y+ multiplier*unitVector[1]
          z = z+ multiplier*unitVector[2]
          modifiedPoint=(x,y,z)
          if cellLocator.FindCell(modifiedPoint)==-1:
            modifiedPoints.SetPoint(i,modifiedPoint)
            self.unitVectors.append(unitVector)
            break
        else: #Opposite Direction
          Switch=True
          x,y,z= OriginalPoint # No Aliasing , Deep Copy
          x = x + (-multiplier)*unitVector[0]
          y = y + (-multiplier)*unitVector[1]
          z = z + (-multiplier)*unitVector[2]
          modifiedPoint=(x,y,z)
          if cellLocator.FindCell(modifiedPoint)==-1:
            modifiedPoints.SetPoint(i,modifiedPoint)
            self.unitVectors.append(numpy.array([-unitVector[0],-unitVector[1],-unitVector[2]]))
            break
          
    self.pathPolydata=testPolydata#Set The testPolydata to the new pathPolydata.
    self.unitVectors.append(numpy.array([0,0,0])) # end point is 0vector as well
    
    #Visualization
    if CATHETER_DEBUG_MOVEDPATH:
      path= PATHDEBUG + "MovedPath-"+self.name + ".vtk"
      self.utility.PolyDataWriter(self.pathPolydata, path)
      x=self.utility.DisplayPolyData("MovedPath-"+self.name, self.pathPolydata)
      x.SetColor(0.5,1,0)
      x.SetAmbient(1)
      x.SetLineWidth(4)
      self.utility.DisplayPoints(self.pathPolydata, "MovedPoints-"+self.name)
    return# End of Move Points
  def XArea(self):
    """This method will cut the original plane with the current path, using
    the ROI box.  
    
    We will generate a series of polygons to represent the original raw path
    data.
    
    This function is tested an working. See PolygonCreation.png
    """
    lengthOfContour=self.pathPolydata.GetNumberOfPoints()
    lengthOfBackLine=self.backLine.GetNumberOfPoints()
    endPoint1=self.pathPolydata.GetPoint(0)
    endPoint2=self.pathPolydata.GetPoint(lengthOfContour-1)
    endPoint3=self.backLine.GetPoint(0)
    endPoint4=self.backLine.GetPoint(lengthOfBackLine-1)
    endPt1=numpy.array(endPoint1)
    endPt2=numpy.array(endPoint2)
    endPt3=numpy.array(endPoint3)
      
    numberOfPoints=lengthOfContour+2 # were only interested in the end points
    # of the back line , since realistically if should define the same line
      
    connection=[endPoint3,endPoint4,endPoint1] # Connect 2-3
    if numpy.linalg.norm(endPt1-endPt3)<numpy.linalg.norm(endPt2-endPt3): 
      connection=[endPoint4,endPoint3,endPoint1] # Connect 2-4
        
    points = vtk.vtkPoints()
    points.SetNumberOfPoints(numberOfPoints)
    for i in range (lengthOfContour):
      points.InsertPoint(i,self.pathPolydata.GetPoint(i)) # ends at endpoint 2
    points.InsertPoint(lengthOfContour,connection[0]) #Second last index
    points.InsertPoint(lengthOfContour+1,connection[1]) #Final Index

    polygon=vtk.vtkPolygon()
    polygon.GetPointIds().SetNumberOfIds(numberOfPoints)
    for i in range(numberOfPoints):
      polygon.GetPointIds().SetId(i,i)

    aPolygonGrid = vtk.vtkUnstructuredGrid()
    aPolygonGrid.Allocate(1, 1)
    aPolygonGrid.InsertNextCell(polygon.GetCellType(), polygon.GetPointIds())
    aPolygonGrid.SetPoints(points)
     
    geometryFilter = vtk.vtkGeometryFilter()
    geometryFilter.SetInputData(aPolygonGrid)
    geometryFilter.Update()
     
    polygonData = geometryFilter.GetOutput()
    
    cutTriangles = vtk.vtkTriangleFilter()
    cutTriangles.SetInputData(polygonData)
    cutTriangles.Update()
    polydata= cutTriangles.GetOutput()
    
    path= PATHDEBUG + "polygon-"+self.name + ".vtk"
    self.utility.PolyDataWriter(polydata, path)
    
    if CATHETER_DEBUG_POLYGON==True:
      self.utility.DisplayPolyData("Polygon"+self.name, polydata)
    return polydata
  def GetUnitVector(self, index,length):
    """ returns the unit vector in mm facing outwards of the face
    """
    if index==0: #We will try to access -1 index if we don't stop this 
      print "Trying to access start point unit vector"
      return self.GetUnitVector(1,length)  #just return the first indexs curvature
    if index==self.pathPolydata.GetNumberOfPoints()-1:
      print "Trying to access end point unit vector"
      return self.GetUnitVector(self.pathPolydata.GetNumberOfPoints()-2,length)
    return self.unitVectors[index]*length
  def TestPointInside(self):
    """ This function uses the XArea and the splined points
    We will determine which of the splines points/midpoints
    are violating the polygon
    """
    cellLocator=vtk.vtkCellLocator()
    cellLocator.SetDataSet(self.XArea)
    cellLocator.LazyEvaluationOn()
    violatingPoints=vtk.vtkPoints()
    polydataCopy=vtk.vtkPolyData()
    polydataCopy.DeepCopy(self.pathPolydata)
    numPoints=self.pathPolydata.GetNumberOfPoints()
    for i in range (1,numPoints-1):
      pathPoint=polydataCopy.GetPoint(i)
      if 0<cellLocator.FindCell(pathPoint):
        print "WARNING: MOVE POINTS OUT FAILED"
        violatingPoints.InsertNextPoint(pathPoint)
    
    if CATHETER_DEBUG_INSIDEVIOLATION:
      polydata=vtk.vtkPolyData()
      polydata.SetPoints(violatingPoints)
      b=self.utility.DisplayPoints(polydata, "InsideViolatingPoints-"+self.name)
      b.SetColor(.5,0,0)
    return
  def IdentifyBadPoints(self):
    """ Taking 3 points and seeing if the Radius defined by it's circle 
    is less than that of the minimum allowed catheter radius.
    TODO: RARE CASE: we should check to make sure the these 3 points are not all co-linear
    then estimating the 3pts circumcenter might fail.
    
    This can only take in polydata that is in order.
    """
    listOfBadPoints=[]
    for i in range (1,len(self.orderedPtIDs) -1 ): # Avoid end points
      #Getting CenterPoint and Radius of curvature
      (centerPoint,R)=self.GetCenterAndCurvature(i)
      if R<self.minCurvature:
        listOfBadPoints.append(self.pathPolydata.GetPoint(i))
        print "Index Of Bad Point: ",i," Radius: ",R
    if CATHETER_DEBUG_BADPOINTS==True:
      polyData=self.utility.PointsToPolyData(listOfBadPoints)
      n=self.utility.DisplayPoints(polyData, "BadPoints-"+self.name)
      n.SetColor(1,0,0) #RED
  def JacobSmoothing(self):
    modifiedPoints=self.pathPolydata.GetPoints()
    lowestCurvature=[] # list where we store lowest curvature values
    concave=[]
    
    for i in range (1,len(self.orderedPtIDs) -1 ): # Avoid end points
      #Getting CenterPoint and Radius of curvature
      A=numpy.array(self.pathPolydata.GetPoint(i-1)) #Gets point in proper order
      B=numpy.array(self.pathPolydata.GetPoint(i))
      C=numpy.array(self.pathPolydata.GetPoint(i+1))
      a = numpy.linalg.norm(C - B)
      b = numpy.linalg.norm(C - A)
      c = numpy.linalg.norm(B - A)
      s = (a + b + c) / 2
      radiusOfCurvature = a*b*c / 4 / numpy.sqrt(s * (s - a) * (s - b) * (s - c))
      lowestCurvature.append(radiusOfCurvature)
      b1 = a*a * (b*b + c*c - a*a)
      b2 = b*b * (a*a + c*c - b*b)
      b3 = c*c * (a*a + b*b - c*c)
      centerPoint = numpy.dot(numpy.column_stack((A, B, C)),(numpy.hstack((b1, b2, b3))))
      centerPoint /= b1 + b2 + b3
      # if the angle between the unit vector (always pointing out) 
      # is 180 degrees it means the curvature is pointing towards the face
      NUMBEROFMM=1   #length of the Unit vector in millimeters
      radiusVector = (centerPoint-B)/ (numpy.linalg.norm(centerPoint-B))*NUMBEROFMM
      unitVector=self.unitVectors[i]
      angle = numpy.arccos(numpy.dot(radiusVector, unitVector)/
                           (numpy.linalg.norm(radiusVector) * numpy.linalg.norm(unitVector)))
      angle=numpy.degrees(angle)
      if angle<90:
        concave.append(False)
      else:
        concave.append(True)
    indexOfInterest=self.findMostConcave(lowestCurvature,concave)
    print indexOfInterest
    
    
  def findMostConcave(self,lowestCurvature, concave):
    lowestIndex=0
    lowestSofar=lowestCurvature[lowestIndex]
    for i in range (len(lowestCurvature)):
      if concave[i] and lowestCurvature[i]<lowestSofar:
        lowestIndex=i
        lowestSofar=lowestCurvature[lowestIndex]
    return lowestIndex+1 #Because we arent taking into account startpoint in our input lists
  def ExpandCurvature(self):
    modifiedPoints=self.pathPolydata.GetPoints()
    for i in range (1,len(self.orderedPtIDs) -1 ): # Avoid end points
      #Getting CenterPoint and Radius of curvature
      A=numpy.array(self.pathPolydata.GetPoint(i-1)) #Gets point in proper order
      B=numpy.array(self.pathPolydata.GetPoint(i))
      C=numpy.array(self.pathPolydata.GetPoint(i+1))
      a = numpy.linalg.norm(C - B)
      b = numpy.linalg.norm(C - A)
      c = numpy.linalg.norm(B - A)
      s = (a + b + c) / 2
      R = a*b*c / 4 / numpy.sqrt(s * (s - a) * (s - b) * (s - c))
      #moving all violated points out 2 Cases
      if R<self.minCurvature: 
        b1 = a*a * (b*b + c*c - a*a)
        b2 = b*b * (a*a + c*c - b*b)
        b3 = c*c * (a*a + b*b - c*c)
        centerPoint = numpy.dot(numpy.column_stack((A, B, C)),(numpy.hstack((b1, b2, b3))))
        centerPoint /= b1 + b2 + b3
        # if the angle between the unit vector (always pointing out) 
        # is 180 degrees it means the curvature is pointing towards the face
        NUMBEROFMM=1   #length of the Unit vector in millimeters
        radiusVector = (centerPoint-B)/ (numpy.linalg.norm(centerPoint-B))*NUMBEROFMM
        unitVector=self.unitVectors[i]
        angle = numpy.arccos(numpy.dot(radiusVector, unitVector)/
                             (numpy.linalg.norm(radiusVector) * numpy.linalg.norm(unitVector)))
        angle=numpy.degrees(angle)
        if angle<90:
          CASE=1 #We Only need to move 1 Point Outwards
        else:
          CASE=2 #We Only need to move 2 Points Outwards
        if CASE==1: # Case 1 where we are moving one point out
          AC_MidPoint=(A+C)/2
          Midpoint_ToCenter_vector= (centerPoint-AC_MidPoint)/ (numpy.linalg.norm(centerPoint-AC_MidPoint))
          AC_MidPoint_Dist=numpy.linalg.norm(AC_MidPoint-A)
          A_To_centerPoint_Dist=self.minCurvature+.10*self.minCurvature
          Mid_A_Center_Angle=numpy.arccos(AC_MidPoint_Dist / A_To_centerPoint_Dist)
          MidPointToCenterDistance=A_To_centerPoint_Dist*numpy.sin(Mid_A_Center_Angle)
          DistanceToMove=A_To_centerPoint_Dist-MidPointToCenterDistance
          NewPointLocation=AC_MidPoint-(DistanceToMove*Midpoint_ToCenter_vector)
          NewPointLocation=NewPointLocation.tolist()
          modifiedPoints.SetPoint(i,NewPointLocation)
        else:  #Case 2 where we are moving 2 points out
          # A , B , C , MAB Midpoint(for AB) , X - CircumCenter 
          #See case2.png for more explaination
          # http://www.mathopenref.com/common/appletframe.html?applet=circumcenter&wid=600&ht=300
          MAB=(A+B)/2
          minCurvature=self.minCurvature+.1*self.minCurvature 
          AtoB_Dist=numpy.linalg.norm(A-B)
          MABtoADist=numpy.linalg.norm(A-MAB)
          ABX_Angle=numpy.arccos(AtoB_Dist**2/(2*minCurvature*AtoB_Dist))
          BAMAC_Angle=numpy.pi-(ABX_Angle)-(numpy.pi/2)
          MACtoA_Dist=numpy.sin(ABX_Angle)*AtoB_Dist
          MABtoIP_Dist=MABtoADist*numpy.tan(BAMAC_Angle)
          V1= (centerPoint-MAB)/ (numpy.linalg.norm(centerPoint-MAB)) #1mm, tested
          IP=MAB+(MABtoIP_Dist*V1)
          V2=(IP-A)/ (numpy.linalg.norm(IP-A))
          New_C=A+V2*MACtoA_Dist*2
          New_C=New_C.tolist()
          modifiedPoints.SetPoint(i+1,New_C)
  def GetCenterAndCurvature(self,index):
    """ Returns as a Tuple containing (CenterPoint[3], CurvatureRadius)
    """
    if index==0 or index==self.pathPolydata.GetNumberOfPoints()-1:
      print "Trying to find index of an invalid point"
      return 
    A=numpy.array(self.pathPolydata.GetPoint(index-1)) #Gets point in proper order
    B=numpy.array(self.pathPolydata.GetPoint(index))
    C=numpy.array(self.pathPolydata.GetPoint(index+1))
    a = numpy.linalg.norm(C - B)
    b = numpy.linalg.norm(C - A)
    c = numpy.linalg.norm(B - A)
    s = (a + b + c) / 2
    R = a*b*c / 4 / numpy.sqrt(s * (s - a) * (s - b) * (s - c))
    b1 = a*a * (b*b + c*c - a*a)
    b2 = b*b * (a*a + c*c - b*b)
    b3 = c*c * (a*a + b*b - c*c)
    centerPoint = numpy.dot(numpy.column_stack((A, B, C)),(numpy.hstack((b1, b2, b3))))
    centerPoint /= b1 + b2 + b3
    return (centerPoint, R)
  def CreateTube(self,tubeRadius,ROI):
    # THIS NEED TO BE IMPLEMENTED . What has to be done 
    # You have to extend the path out towards the start and end points (perhabs make it flush with the
    # roi wall if there is no smoothing that has to be done) the tube filter needs to extend past the mask.
    extendedPath=self.ExtendPath(self.pathPolydata)
    catheterHole=vtk.vtkTubeFilter()
    catheterHole.CappingOn()
    catheterHole.SetInputData(extendedPath)
    catheterHole.SetNumberOfSides(100)
    catheterHole.SetRadius(tubeRadius)
    catheterHole.Update()
    # Normals are for subtraction via polydata later , during the creation of the mask
    normalsFunction = vtk.vtkPolyDataNormals()
    normalsFunction.AutoOrientNormalsOn()
    normalsFunction.AddInputConnection(catheterHole.GetOutputPort())
    normalsFunction.Update()
    polydata=normalsFunction.GetOutput()
    
    if CATHETER_DEBUG_TUBE:
      path= PATHDEBUG + "Tube-"+self.name + ".vtk"
      self.utility.PolyDataWriter(extendedPath, path)
      x=self.utility.DisplayPolyData("Tube-"+self.name, normalsFunction.GetOutput())
      x.SetColor(0.1,1,0)
      x.SetOpacity(0.20)
      x.SetAmbient(1)
      x.EdgeVisibilityOn()
      x.SetLineWidth(1)
    return polydata
  def ExtendPath(self,path):
    """ Extends the path in the direction of the last direction vector on that end.
    Assumes the points are ordered coming in
    """
    numberOfPoints=path.GetNumberOfPoints()+2
    points=path.GetPoints()
    newPoints=vtk.vtkPoints()
    newPoints.SetNumberOfPoints(numberOfPoints)
    #Extending left point
    leftEnd=points.GetPoint(0) # assumes the points are ordered 
    a,b,c=leftEnd
    leftEnd2=points.GetPoint(1)
    a2,b2,c2=leftEnd2
    d1,d2,d3=a-a2,b-b2,c-c2
    newleftPoint=(a+d1,b+d2,c+d3)
    #Extending right point
    rightEnd=points.GetPoint(numberOfPoints-3) # assumes the points are ordered 
    print rightEnd
    a,b,c=rightEnd
    rightEnd2=points.GetPoint(numberOfPoints-4)
    print rightEnd2
    a2,b2,c2=rightEnd2
    d1,d2,d3=a-a2,b-b2,c-c2
    newRightPoint=(a+d1,b+d2,c+d3)
    
    #Setting Points
    newPoints.SetPoint(0,newleftPoint)
    for i in range (path.GetNumberOfPoints()):
      newPoints.SetPoint(i+1,points.GetPoint(i))
    newPoints.SetPoint(numberOfPoints-1,newRightPoint)
    
    #Rebuilding the polydata
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(numberOfPoints)
    for i in range (numberOfPoints):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPd=vtk.vtkPolyData()
    newPd.SetPoints(newPoints)
    newPd.SetLines(cellArray)
    return newPd
    
class Util_HDR:
  """ This is a Utility class with alot of Non-Specific methods
  """
  def createVolumeFromRoi(self, exportRoi, spacingMm):
    """Creates a volume node with image data of proper spacing inside of it"""
    roiCenter = [0, 0, 0]
    exportRoi.GetXYZ( roiCenter )
    roiRadius = [0, 0, 0]
    exportRoi.GetRadiusXYZ( roiRadius )
    roiOrigin_Roi = [roiCenter[0] - roiRadius[0], roiCenter[1] - roiRadius[1], roiCenter[2] - roiRadius[2], 1 ]

    roiToRas = vtk.vtkMatrix4x4()
    if exportRoi.GetTransformNodeID() != None:
      roiBoxTransformNode = slicer.mrmlScene.GetNodeByID(exportRoi.GetTransformNodeID())
      roiBoxTransformNode.GetMatrixTransformToWorld(roiToRas)

    exportVolumeSize = [roiRadius[0]*2/spacingMm, roiRadius[1]*2/spacingMm, roiRadius[2]*2/spacingMm]
    exportVolumeSize = [int(math.ceil(x)) for x in exportVolumeSize]

    exportImageData = vtk.vtkImageData()
    exportImageData.SetExtent(0, exportVolumeSize[0]-1, 0, exportVolumeSize[1]-1, 0, exportVolumeSize[2]-1)
    if vtk.VTK_MAJOR_VERSION <= 5:
      exportImageData.SetScalarType(vtk.VTK_DOUBLE)
      exportImageData.SetNumberOfScalarComponents(3)
      exportImageData.AllocateScalars()
    else:
      exportImageData.AllocateScalars(vtk.VTK_DOUBLE, 1)
      
    exportVolume = slicer.vtkMRMLScalarVolumeNode()
    exportVolume.SetAndObserveImageData(exportImageData)
    exportVolume.SetIJKToRASDirections( roiToRas.GetElement(0,0), roiToRas.GetElement(0,1), roiToRas.GetElement(0,2), roiToRas.GetElement(1,0), roiToRas.GetElement(1,1), roiToRas.GetElement(1,2), roiToRas.GetElement(2,0), roiToRas.GetElement(2,1), roiToRas.GetElement(2,2))
    exportVolume.SetSpacing(spacingMm, spacingMm, spacingMm)
    roiOrigin_Ras = roiToRas.MultiplyPoint(roiOrigin_Roi)
    exportVolume.SetOrigin(roiOrigin_Ras[0:3])
    return exportVolume
  
  def polyDataToImageData(self, polydata, referenceVolumeNode):
    """ The first part of this was taken from vtkPolyDataToLabelmapFilter.cxx
    to get the polydata preprocessed before creating the image data"""
    normalsFunction=vtk.vtkPolyDataNormals()
    normalsFunction.SetInputData(polydata)
    normalsFunction.ConsistencyOn()
    normalsFunction.Update()
    trigFilter=vtk.vtkTriangleFilter()
    trigFilter.SetInputData(normalsFunction.GetOutput())
    trigFilter.Update()
    stripper=vtk.vtkStripper()
    stripper.SetInputData(trigFilter.GetOutput())
    stripper.Update()
    pd=stripper.GetOutput()
    
    """  
    ANDRAS ---- Below is the code that I am unsure about . 
    How do we set up the image data to get its information from the referenceVolumeNode
    """
    whiteImage=vtk.vtkImageData()
    spacing=[1,1,1]
    bounds=[0,0,0,0,0,0]
    origin=[0,0,0]
    pd.GetBounds(bounds)
    dim=[0,0,0]
    math.ceil(3.4)
    for i in range (3):
      dim[i]=int(math.ceil((bounds[i*2+1]-bounds[i*2])/ spacing[i]))
    #whiteImage.SetDimensions(dim)
    whiteImage.SetExtent(0,dim[0]-1,0,dim[1]-1,0,dim[2]-1)
    origin[0]= bounds[0]+spacing[0]/2
    origin[1] = bounds[2]+spacing[1]/2
    origin[2] = bounds[4] +spacing[2]/2
    #whiteImage.SetOrigin(origin)
    whiteImage.AllocateScalars(vtk.VTK_UNSIGNED_CHAR,1)
    inval=255
    outval = 0
    count = whiteImage.GetNumberOfPoints()
    i=0
    while i<count:
      whiteImage.GetPointData().GetScalars().SetTuple1(i,inval)
      i+=1
    
    pol2stenc= vtk.vtkPolyDataToImageStencil()
    pol2stenc.SetInputData(pd)
    #pol2stenc.SetOutputOrigin(origin)
    #pol2stenc.SetOutputSpacing(spacing)
    pol2stenc.SetOutputWholeExtent(whiteImage.GetExtent())
    pol2stenc.Update()
    
    imgstenc= vtk.vtkImageStencil()
    imgstenc.SetInputData(whiteImage)
    imgstenc.SetStencilConnection(pol2stenc.GetOutputPort())
    imgstenc.ReverseStencilOff()
    imgstenc.SetBackgroundValue(outval)
    imgstenc.Update()
    self.DisplayImageData(imgstenc.GetOutput())
    print "Done"
    
    
  def DisplayVolumeNode(self, volumeNode, name="Volume"):
    existingVolumeNode=slicer.util.getNode(name)
    if not existingVolumeNode:
      displayNode=slicer.vtkMRMLScalarVolumeDisplayNode()
      displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
      volumeNode.SetName(name)
      slicer.mrmlScene.AddNode(volumeNode)
      slicer.mrmlScene.AddNode(displayNode)
      volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
    else:
      existingVolumeNode.SetImageData(volumeNode.GetImageData())
      existingVolumeNode.SetIJKToRAS(volumeNode.GetIJKToRAS())
    return

  def DisplayImageData(self, imageData, name="ImageNode"):
    volumeNode=slicer.util.getNode(name)
    if (not volumeNode):
      displayNode=slicer.vtkMRMLScalarVolumeDisplayNode()
      displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
      volumeNode=slicer.vtkMRMLScalarVolumeNode()
      volumeNode.SetName(name)
      slicer.mrmlScene.AddNode(volumeNode)
      slicer.mrmlScene.AddNode(displayNode)
      volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
    volumeNode.SetAndObserveImageData(imageData)
    return
  def GetMidPoint(self,p1,p2):
    """ Gets the midpoint between two points in space 
    """
    a,b,c=p1
    d,e,f=p2
    return ((a+d)/2,(b+e)/2,(c+f)/2)
  def PointsToPolyData(self,listOfPoints):
    """ Converts 3D list of points of an array into a polyData line
    The connections between this line are simply the order in which 
    they are provided
    """
    points=vtk.vtkPoints()
    idlist = vtk.vtkIdList()
    numOfPoints=len(listOfPoints)
    if numOfPoints==0:
      print ("WARNING:No points to convert to polyData")
      return vtk.vtkPolyData() #returning Blank PolyData
    points.SetNumberOfPoints(numOfPoints)
    for i in range (numOfPoints):
      points.InsertPoint(i, listOfPoints[i]) #Add the points
      idlist.InsertNextId(i)
    polyData=vtk.vtkPolyData()
    polyData.Allocate()
    polyData.InsertNextCell(vtk.VTK_LINE,idlist)
    polyData.SetPoints(points)
    return polyData
  def DisplayPoints(self, polyDataLine,name):
    """ Will display all of the points of a given Polydata Line
    """
    sphere= vtk.vtkSphereSource()
    sphere.SetRadius(0.3)
    sphere.Update()
    glyphFilter=vtk.vtkGlyph3D()
    glyphFilter.ScalingOff()
    glyphFilter.SetSourceData(sphere.GetOutput()) #object at eachPoint
    glyphFilter.SetInputData(polyDataLine)
    glyphFilter.Update()
    node=self.DisplayPolyData(name, glyphFilter.GetOutput())
    node.SetColor(0.3,0.4,1) #Max 1 for each column
    node.SetAmbient(1)
    return node
  def PolyDataWriter(self, polyData, path):
    """ Creates a vtk file for the given path
    The path must be a valid file location and name for the file
    .vtk is recommended to be at the end
    AVOID spaces in the filename and path
    """
    w = vtk.vtkPolyDataWriter()
    w.SetInputData(polyData)
    w.SetFileTypeToASCII()
    w.SetFileName(path)
    w.Write()
  def PolyDataToList(self,polyData):
    """ This won't work for all polyData
    """
    points=polyData.GetPoints() #vtkPoints
    numOfPoints=points.GetNumberOfPoints() #vtkPoints functions
    listOfPoints=[]
    for i in range(numOfPoints):
      listOfPoints.append(points.GetPoint(i))
    return listOfPoints  
  def DotProduct(self, v1, v2):
    v1a,v1b,v1c =v1[0],v1[1],v1[2]
    v2a,v2b,v2c =v2[0],v2[1],v2[2]
    return v1a*v2a+v1b*v2b+v1c*v2c
  def UnpackPoints(self, markupNode):
    """ Takes a node as given by the widgit and returns a python
    list of the points in R-A-S format.
    """
    numOfPlanes=markupNode.GetNumberOfFiducials()
    listOfPoints=[]
    for i in range(numOfPlanes):
      point=[0,0,0]# have to use a the C++ style of getter (see API)
      markupNode.GetNthFiducialPosition(i, point) #unpacking point
      listOfPoints.append(point)
    return listOfPoints
  def GetRulerVector(self, ruler):
    # x is L->R, y is P->A, z is I->S
    """ Takes ruler and returns a vector [x,y,z]
    x is L->R, y is P->A, z is I->S
    """
    position1=[0,0,0]
    position2=[0,0,0]
    ruler.GetPosition1(position1)
    ruler.GetPosition2(position2)
    return self.GetVector(position1, position2)
  def GetVector(self,point1,point2):
    """ Returns a vector given two points
    """
    vector=[0,0,0]
    for i in range(len(point1)):
      vector[i]=point2[i]-point1[i]
    return vector
  def CrossProduct(self,v1,v2):
    temp=[0,0,0]
    temp[0]=v1[1]*v2[2]-v1[2]*v2[1]
    temp[1]=v1[2]*v2[0]-v1[0]*v2[2]
    temp[2]=v1[0]*v2[1]-v1[1]*v2[0]
    return temp
  def CreateNewNode(self,nodeName, nodeType="vtkMRMLModelNode", overwrite=True):
      """Create new node from scratch
      """
      scene = slicer.mrmlScene
      newNode = scene.CreateNodeByClass(nodeType)
      newNode.UnRegister(scene)
      self.AddNodeToMRMLScene(newNode, nodeName, overwrite)
      return newNode
  def AddNodeToMRMLScene(self,newNode, nodeName='default', overwrite=True):
      scene = slicer.mrmlScene
      if not overwrite:
        nodeName = scene.GetUniqueNameByString(nodeName)
      newNode.SetName(nodeName)
      if overwrite:
        self.removeOldMRMLNode(newNode)
      scene.AddNode(newNode)
  def removeOldMRMLNode(self,node):
      """Overwrite a MRML node with the same name and class as the given node
      """
      scene = slicer.mrmlScene
      collection = scene.GetNodesByClassByName(node.GetClassName(), node.GetName())
      if collection.GetNumberOfItems() == 1:
        oldNode = collection.GetItemAsObject(0)
        scene.RemoveNode(oldNode)
      elif collection.GetNumberOfItems() > 1:
        # This should never happen
        raise Exception("Unable to determine node to replace! Too many existing.")
      else:
        # There was no node to overwrite
        return 1
      return 0
  def DisplayPolyData(self, nameOfNode, polyData, overwrite=True):
    """ Function that Overwrites/Creates a Node to display Polydata
    """
    n=self.CreateNewNode(nameOfNode, "vtkMRMLModelNode", overwrite=True)
    outputMouldModelDisplayNode = slicer.vtkMRMLModelDisplayNode()
    slicer.mrmlScene.AddNode(outputMouldModelDisplayNode)
    outputMouldModelDisplayNode.BackfaceCullingOff()
    n.SetAndObserveDisplayNodeID(outputMouldModelDisplayNode.GetID())
    n.SetAndObservePolyData(polyData)
    return outputMouldModelDisplayNode
  def TurnOffDisplay(self,name):
    """ will turn off whatever node name given from the display 
    """
    x=slicer.mrmlScene.GetNodesByName(name)
    y=x.GetItemAsObject(0)
    z=y.GetDisplayNode()
    if z==None:
      raise Exception ("No node named: " +name)
    z.SetVisibility(0)
  def DisplayImplicit(self,name,implicitFunction, ROI=None, Extents=None):
    """This function takes an implicitFunction and displays it within the ROI
    It will return the modelDisplaynode assosiated with in so that attributes 
    can be changed
    """
    sampleFunction=vtk.vtkSampleFunction()
    sampleFunction.SetSampleDimensions(70,70,70)
    sampleFunction.SetImplicitFunction(implicitFunction)
    ROIExtents=[0,0,0,0,0,0]
    if ROI==None:
      ROIExtents=Extents
    else:
      ROIExtents=self.GetROIExtents(ROI)
    sampleFunction.SetModelBounds(ROIExtents)
    sampleFunction.Update()
    contourFilter=vtk.vtkContourFilter()
    contourFilter.SetInputConnection(sampleFunction.GetOutputPort())
    contourFilter.GenerateValues(1,0,0)
    contourFilter.Update()
    polyData=contourFilter.GetOutput()
    modelDisplayNode=self.DisplayPolyData(name,polyData)
    return modelDisplayNode
  def ExpandExtents(self,ROIExtents, value):
    """ This Expands the ROIExtents which define a box, so it makes 
    the area larger by the passed in value
    """
    newROI=[0,0,0,0,0,0]
    evenNumber=True
    for index in range(len(ROIExtents)):
      if evenNumber==True:
        newROI[index]=ROIExtents[index]-value
        evenNumber=False
      else:
        newROI[index]=ROIExtents[index]+value
        evenNumber=True
    return newROI
  def GetROIExtents(self, ROI):
    """Returns the xmin, xmax, ymin, ymax,zmin,zmax of the ROI box
    """
    ROICenterPoint = [0,0,0]
    ROI.GetXYZ(ROICenterPoint)
    ROIRadii = [0,0,0]
    ROI.GetRadiusXYZ(ROIRadii)
    ROIExtents = [0,0,0,0,0,0]
    ROIExtents[0] = ROICenterPoint[0] - ROIRadii[0]
    ROIExtents[1] = ROICenterPoint[0] + ROIRadii[0]
    ROIExtents[2] = ROICenterPoint[1] - ROIRadii[1]
    ROIExtents[3] = ROICenterPoint[1] + ROIRadii[1]
    ROIExtents[4] = ROICenterPoint[2] - ROIRadii[2]
    ROIExtents[5] = ROICenterPoint[2] + ROIRadii[2]
    return ROIExtents
  def GetROIPoints(self,ROI):
    """ RAS 
    L->R  Index [0],[1]
    P->A  Index[2],[3]
    I->S  Index[4],[5]
    """
    ROICenterPoint = [0,0,0]
    ROI.GetXYZ(ROICenterPoint)
    ROIRadii = [0,0,0]
    ROI.GetRadiusXYZ(ROIRadii)
    ROIPoints=[]
    ROIPoints.append([ROICenterPoint[0]-ROIRadii[0],ROICenterPoint[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0]+ROIRadii[0],ROICenterPoint[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1]-ROIRadii[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1]+ROIRadii[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1],ROICenterPoint[2]-ROIRadii[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1],ROICenterPoint[2]+ROIRadii[2]])
    return ROIPoints
  def GetClosestExtent(self,ruler,ROI):
    """ Returns the index of the closest ROI Extent to the second point
    on the ruler. 
    Asserted that the second point of the ruler is closest to the front 
    extent of the ROI box.
    """
    roiPoints=self.GetROIPoints(ROI)
    position2=[0,0,0]
    ruler.GetPosition2(position2) #Back end of the ruler
    rulerPt=numpy.array(position2)
    closestIndex=0
    for i in range (1,6):
      priorPt=numpy.array(roiPoints[closestIndex])
      nextPt=numpy.array(roiPoints[i])
      #distance functions
      if numpy.linalg.norm(rulerPt-priorPt)>numpy.linalg.norm(rulerPt-nextPt):
        closestIndex=i
    return closestIndex
  def GetOppositeExtent(self,RoiIndex):
    """ A pretty simple function that I only created to improve readibility
    This will just get the ROI extent's opposite point
    In the RAS coordinate System
    RAS 
    L->R  Index [0],[1]
    P->A  Index[2],[3]
    I->S  Index[4],[5]
    
    """
    if RoiIndex%2==0: # Even
      return RoiIndex+1
    else: 
      return RoiIndex-1
  def SortPointsInPlane(self, listOfPoints, vectorPlane):
    """ Sorts points in order based on their distance along the plane in the 
    VectorPlane Direction
    """
    if listOfPoints == []: 
      return []
    else:
      pivot= listOfPoints[0]
      pivotValue = self.DotProduct(pivot,self.catheterVector)
      lesser = self.SortPointsInPlane([x for x in listOfPoints[1:] if
                                 self.utility.DotProduct(x, self.catheterVector) <
                                  pivotValue], self.catheterVector )
      greater= self.SortPointsInPlane([x for x in listOfPoints[1:] if
                                 self.utility.DotProduct(x, self.catheterVector) >=
                                  pivotValue], self.catheterVector)
    return lesser + [pivot] + greater
    
    
