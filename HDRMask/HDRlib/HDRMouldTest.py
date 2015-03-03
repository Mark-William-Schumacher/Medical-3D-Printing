from __main__ import slicer, vtk , qt

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