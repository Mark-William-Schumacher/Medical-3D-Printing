from Utility import *

class CatheterPath:

  """ This class only owns a minimum distance mask and an
  implicit plane
  Generation of the path is done step wise so that If Debug is on
  we can analyze the output of each individual step
  """
  def __init__(self, minimumDistanceMask, implicitPlane, minCurvature , ID, backLine,
    CATHETER_DEBUG_POLYGON, CATHETER_DEBUG_RAW_POINTS, CATHETER_DEBUG_RAW_PATH, CATHETER_DEBUG_RECONSTRUCT,
    CATHETER_DEBUG_SPLINE, CATHETER_DEBUG_INSIDEVIOLATION, CATHETER_DEBUG_SHOWCIRCLES, CATHETER_DEBUG_MOVEDPATH,
    CATHETER_DEBUG_SMOOTHEDPATH, CATHETER_DEBUG_TUBE, CATHETER_DEBUG_BADPOINTS, PATHDEBUG, ALGOO):
  
    self.CATHETER_DEBUG_POLYGON=         CATHETER_DEBUG_POLYGON
    self.CATHETER_DEBUG_RAW_POINTS=      CATHETER_DEBUG_RAW_POINTS #Show Raw Path Points-Costly to visualize
    self.CATHETER_DEBUG_RAW_PATH=        CATHETER_DEBUG_RAW_PATH
    self.CATHETER_DEBUG_RECONSTRUCT=     CATHETER_DEBUG_RECONSTRUCT
    self.CATHETER_DEBUG_SPLINE=          CATHETER_DEBUG_SPLINE
    self.CATHETER_DEBUG_INSIDEVIOLATION= CATHETER_DEBUG_INSIDEVIOLATION
    self.CATHETER_DEBUG_SHOWCIRCLES =    CATHETER_DEBUG_SHOWCIRCLES
    self.CATHETER_DEBUG_MOVEDPATH =      CATHETER_DEBUG_MOVEDPATH
    self.CATHETER_DEBUG_SMOOTHEDPATH =   CATHETER_DEBUG_SMOOTHEDPATH
    self.CATHETER_DEBUG_TUBE =           CATHETER_DEBUG_TUBE  #shows the channels and tubes
    self.CATHETER_DEBUG_BADPOINTS =      CATHETER_DEBUG_BADPOINTS
    self.PATHDEBUG                =      PATHDEBUG
    self.ALGOO =                         ALGOO
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
    path= self.PATHDEBUG + "RawPath-"+self.name + ".vtk"
    self.utility.PolyDataWriter(unconnectedPolydata, path) #creates .vtk File
    if self.CATHETER_DEBUG_RAW_POINTS: # Very Time Consuming 1-2 seconds to Generate each path
      self.utility.DisplayPoints(unconnectedPolydata,"RawPoints-"+self.name)
    if self.CATHETER_DEBUG_RAW_PATH:
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
    path= self.PATHDEBUG + "ReconstructedPath-"+self.name + ".vtk"
    self.utility.PolyDataWriter(newPolyData, path)
    if self.CATHETER_DEBUG_RECONSTRUCT:
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
    
    if self.CATHETER_DEBUG_SPLINE:
      path= self.PATHDEBUG + "SplinePath-"+self.name + ".vtk"
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
    for i in range (int(self.ALGOO)):
      self.ExpandCurvature()
    self.SplinePath()
    if self.CATHETER_DEBUG_SMOOTHEDPATH:
      path= self.PATHDEBUG + "SmoothedPath-"+self.name + ".vtk"
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
    if self.CATHETER_DEBUG_MOVEDPATH:
      path= self.PATHDEBUG + "MovedPath-"+self.name + ".vtk"
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
    
    path= self.PATHDEBUG + "polygon-"+self.name + ".vtk"
    self.utility.PolyDataWriter(polydata, path)
    
    if self.CATHETER_DEBUG_POLYGON==True:
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
    
    if self.CATHETER_DEBUG_INSIDEVIOLATION:
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
    if self.CATHETER_DEBUG_BADPOINTS==True:
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
  def CreateTube(self,tubeRadius,ROI, name):
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
    
    if self.CATHETER_DEBUG_TUBE:
      path= self.PATHDEBUG + name+"-"+self.name + ".vtk"
      self.utility.PolyDataWriter(extendedPath, path)
      x=self.utility.DisplayPolyData(name+"-"+self.name, normalsFunction.GetOutput())
      x.SetColor(0.5,0.1,1)
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