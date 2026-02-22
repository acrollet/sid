import unittest
import xml.etree.ElementTree as ET
from pippin.utils.wda import _xml_to_element

class TestWDA(unittest.TestCase):
    def test_xml_to_element_parsing(self):
        xml_str = """
        <AppiumAUT>
            <XCUIElementTypeWindow type="XCUIElementTypeWindow" x="0" y="0" width="375" height="812">
                <XCUIElementTypeButton type="XCUIElementTypeButton" name="btn1" label="Login" x="10" y="20" width="100" height="50" />
                <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="lbl" label="Greeting" value="Hello" x="0" y="0" width="0" height="0" />
            </XCUIElementTypeWindow>
        </AppiumAUT>
        """
        root = ET.fromstring(xml_str)
        el = _xml_to_element(root)

        self.assertEqual(el["role"], "application")
        self.assertEqual(len(el["nodes"]), 1)
        
        window = el["nodes"][0]
        self.assertEqual(window["role"], "Window")
        self.assertEqual(window["frame"]["width"], 375.0)
        self.assertEqual(len(window["nodes"]), 2)

        btn = window["nodes"][0]
        self.assertEqual(btn["role"], "Button")
        self.assertEqual(btn["AXIdentifier"], "btn1")
        self.assertEqual(btn["AXLabel"], "Login")
        self.assertEqual(btn["frame"]["x"], 10.0)
        self.assertEqual(btn["frame"]["y"], 20.0)
        self.assertEqual(btn["frame"]["width"], 100.0)

        lbl = window["nodes"][1]
        self.assertEqual(lbl["role"], "StaticText")
        self.assertEqual(lbl["AXLabel"], "Greeting")
        self.assertEqual(lbl["AXValue"], "Hello")
        # Wait, the logic adds frame if x and y are in attrib. Yes, frame is added.
        self.assertEqual(lbl["frame"]["width"], 0.0)

if __name__ == '__main__':
    unittest.main()
