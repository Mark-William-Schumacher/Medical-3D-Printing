""" This Module and algorithm was designed my Mark Schumacher while working with the PERK Lab 
    in Kingston Ontario. The module is build to run in Slicer 4.40 """
    
    
""" The Following Debug variables are used to visualize different parts of the algorithm """ 
ROOTPATH = "C:\\MakeHDRApplicatorMask\\" # This is where doc, src and data should be
PATHDEBUG= ROOTPATH+"\\doc\\DebugPolyData\\" #Where to store poldata Writter output
DEBUG_CLIPPING= False
DEBUG_CONNECTIVITYFACE= True
DEBUG_CUTTINGPLANES= False
DEBUG_MINMASK= False
DEBUG_RAWPATH= False
DEBUG_SLITPLANES=False
DEBUG_BUBBLEMASK= False
CATHETER_DEBUG_POLYGON=False
CATHETER_DEBUG_RAW_POINTS=False #Show Raw Path Points-Costly to visualize
CATHETER_DEBUG_RAW_PATH=False
CATHETER_DEBUG_RECONSTRUCT=False
CATHETER_DEBUG_SPLINE=False
CATHETER_DEBUG_INSIDEVIOLATION=False
CATHETER_DEBUG_SHOWCIRCLES=False
CATHETER_DEBUG_MOVEDPATH=False
CATHETER_DEBUG_SMOOTHEDPATH=False
CATHETER_DEBUG_TUBE=False  #shows the channels and tubes
CATHETER_DEBUG_BADPOINTS=False
    
import os
import unittest
import numpy
import time
from __main__ import vtk, qt, ctk, slicer
import math
from HDRlib import *

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
    parent.contributors = ["Mark Schumacher,Jacob Andreou, Ian Cumming, \
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
    self.cathRadiusSlider.value = 1.4
    parametersFormLayout.addRow("Catheter Radius ", self.cathRadiusSlider)
    

    # Catheter path minimum radius of curvature value - slider and spinbox
    self.minCurvatureSlider = ctk.ctkSliderWidget()
    self.minCurvatureSlider.toolTip = "Defines the minimum radius of \
    curvature of any point along the catheter paths, in mm. "
    self.minCurvatureSlider.minimum = 0
    self.minCurvatureSlider.maximum = 60
    self.minCurvatureSlider.value = 14
    parametersFormLayout.addRow("Catheter Curvature ",
                                 self.minCurvatureSlider)
    
    # Output mould model resolution value - slider and spinbox
    self.algorythm = ctk.ctkSliderWidget()
    self.algorythm.toolTip = "How Many Cycles to smooth"
    self.algorythm.minimum = 0
    self.algorythm.maximum = 1000
    self.algorythm.value = 500
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
    
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))

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
        # Remove the old node if it exists

      
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
      
    x=slicer.mrmlScene.GetNodesByName("R")
    if x.GetNumberOfItems()!=0:
      y=x.GetItemAsObject(0)
      self.roiComboBox.setCurrentNode(y)
      
    x=slicer.mrmlScene.GetNodesByName("StartPoints")
    if x.GetNumberOfItems()!=0:
      y=x.GetItemAsObject(0)
      self.startPointComboBox.setCurrentNode(y)
  def CreateTestObject(self):
    TestObject()
  def CreateMould(self):
    
    """ The "main" of our entire program, Start here.
    This is the Method that gets run upon clicking of the 
    createMouldButton defined in Setup. 
    """
    
    
    MINIMUMTHICKNESSMM  =   10 # We need to dilate so that the thickness of the mask is about 2mm at all sections 
    print("HDRMouldWidget::Apply Mould Button Pressed")
    mouldLogic = MouldLogic(self.startPointComboBox, DEBUG_CONNECTIVITYFACE, DEBUG_SLITPLANES, ROOTPATH) #number of paths total
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
    mouldLogic.minimumDistanceMask = mouldLogic.MinimumDistanceMask(clippedFace,
                                         distanceFromTubeCenter, ROI, ruler)
    if DEBUG_MINMASK:
      utility.DisplayPolyData("Minimum-Distance-Mask", mouldLogic.minimumDistanceMask)
      utility.PolyDataWriter(mouldLogic.minimumDistanceMask,
                                "C:\\MakeHDRApplicatorMask\\doc\\"+\
                                "DebugPolyData\\MinMask.vtk")
      
    mouldLogic.bubbleMask = mouldLogic.MinimumDistanceMask(clippedFace,
                                         distanceFromTubeCenter, ROI, ruler, True)
    if DEBUG_BUBBLEMASK:
      utility.DisplayPolyData("Bubble-Mask", mouldLogic.bubbleMask)
    
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
          mouldLogic.listOfPlanes[i],minCurvature, str(i), mouldLogic.listOfBackLines[i], 
          CATHETER_DEBUG_POLYGON, CATHETER_DEBUG_RAW_POINTS, CATHETER_DEBUG_RAW_PATH, CATHETER_DEBUG_RECONSTRUCT,
          CATHETER_DEBUG_SPLINE, CATHETER_DEBUG_INSIDEVIOLATION, CATHETER_DEBUG_SHOWCIRCLES, CATHETER_DEBUG_MOVEDPATH,
          CATHETER_DEBUG_SMOOTHEDPATH, CATHETER_DEBUG_TUBE, CATHETER_DEBUG_BADPOINTS, PATHDEBUG, self.algorythm.value)
    
      #Move all of these to a GetTube Function
      mouldLogic.tubes.append(catheterPath.CreateTube(self.cathRadiusSlider.value,ROI, "tube"))
      mouldLogic.channels.append(catheterPath.CreateTube(self.cathRadiusSlider.value+MINIMUMTHICKNESSMM/2,ROI, "channel"))
      slitSize=self.slitThickness.value
      mouldLogic.CreateSlit(mouldLogic.listOfNormals[i],
                            catheterPath.pathPolydata,
                            ruler,ROI,slitSize) #appends to self.slitPlanes
                                                                                                                                                                                                                                                  
    print ("Converting to Binarized Images")
    SIZEOFVOXELMM       =   0.1 #mm
    referenceVolume     =   utility.CreateVolumeFromRoi(ROI,SIZEOFVOXELMM) #vtkMRMLScalarVolumeNode()
    tubesAsImageData    =   []  # This is a container for the vtkImageData of the tubes
    slitsAsImageData    =   []
    channelsAsImageData =   [] # Channels encase the tubes
    
    for i in range (len(mouldLogic.tubes)):
      tubesAsImageData.append(utility.PolyDataToImageData(mouldLogic.tubes[i],referenceVolume,255,0)) #vtkImageData
      slitsAsImageData.append(utility.PolyDataToImageData(mouldLogic.slitPlanes[i],referenceVolume,255,0))
      channelsAsImageData.append(utility.PolyDataToImageData(mouldLogic.channels[i],referenceVolume,255,0))
    mergedTubeImages        =   utility.MergeAllImages(tubesAsImageData) #And operations on all the tube imageData
    mergedSlitImages        =   utility.MergeAllImages(slitsAsImageData)
    mergedChannels          =   utility.MergeAllImages(channelsAsImageData)
    clippedFace             =   utility.PolyDataToImageData(mouldLogic.skinSurface,referenceVolume,0,255)  
    bubbleMask              =   utility.PolyDataToImageData(mouldLogic.bubbleMask,referenceVolume,0,255)
    dilatedFace             =   utility.ImageAND(clippedFace,bubbleMask)
    partialSlits            =   utility.ImageAND(mergedSlitImages,dilatedFace)
    negatedChannels         =   utility.ImageNegation(mergedChannels,referenceVolume)
    outerBoundaryMask       =   utility.ImageAND(negatedChannels,dilatedFace)
    negatedOuterBoundary    =   utility.ImageNegation(outerBoundaryMask,referenceVolume)
    solidPlasticMould       =   utility.ImageXOR(negatedOuterBoundary,clippedFace)
    plasticMouldWithoutTubes=   utility.ImageOR(solidPlasticMould,mergedTubeImages)
    negatedcompletedMould   =   utility.ImageOR(plasticMouldWithoutTubes,partialSlits)
    completedMould          =   utility.ImageNegation(negatedcompletedMould,referenceVolume)
#     
#     
    utility.DisplayImageData(completedMould,referenceVolume, "completedMould")
#     utility.DisplayImageData(outerBoundaryMask,referenceVolume, "outerBoundaryMask")
#     utility.DisplayImageData(mergedTubeImages,referenceVolume, "mergedTubes")
#     utility.DisplayImageData(mergedSlitImages,referenceVolume, "mergedSlits")
#     utility.DisplayImageData(partialSlits,referenceVolume, "partialSlits")
#     utility.DisplayImageData(clippedFace,referenceVolume, "clippedFace")
#     utility.DisplayImageData(mouldImageWithoutTubes,referenceVolume, "mouldImageWithoutTubes")
    
   

