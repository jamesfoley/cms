"""Unit tests for the various CMS utilities."""


import cStringIO, datetime

from django.test.testcases import TestCase

from cms.apps.utils import remote, xml, iteration
from cms.apps.utils.models import CachedRemoteResource


class CachedIteratorTest(TestCase):
    
    """Tests the cached interator functionality."""
    
    def testCacheIsActive(self):
        """Tests that a cached iterator actually caches items!"""
        iterator = iteration.cache(xrange(4))
        # Iterator once.
        for item_1 in iterator:
            pass
        self.assertEqual(item_1, 3)
        # Iterate twice.
        for item_2 in iterator:
            pass
        self.assertEqual(item_2, 3)
        
    def testRandomAccess(self):
        """Tests that a cached iterator actually caches items!"""
        iterator = iteration.cache(xrange(4))
        self.assertEqual(len(iterator), 4)
        self.assertEqual(iterator[0], 0)
        self.assertEqual(iterator[2], 2)
        self.assertRaises(IndexError, lambda: iterator[4])
        self.assertEqual(iterator[0:4], [0, 1, 2, 3])


OK_URL = "http://www.etianen.com/"

MISSING_URL = "http://www.etianen.com/foo/bar/"


class RemoteTest(TestCase):
    
    """Tests that the remote library works."""
    
    def testGetRequest(self):
        """Tests that a vanilla GET request works."""
        response = remote.open(OK_URL)
        self.assertContains(response, "Enlightened Website Development")
        
    def testBrokenLink(self):
        """Tests that broken links are handled correctly."""
        # The first method should raise an error.
        self.assertRaises(remote.HttpError, remote.open, MISSING_URL)
        # The second method should return an error response.
        response = remote.open(MISSING_URL, require_success=False)
        self.assertContains(response, "Page Not Found", status_code=404)
        
    def testQuery(self):
        """Tests that data can be sent using GET."""
        response = remote.open("http://www.girton.cam.ac.uk/news/", query={"page": 2})
        self.assertContains(response, "Page 2")
        
    def testPost(self):
        """Tests that a post request can be sent."""
        response = remote.open("http://www.etianen.com/admin/", {"username": "david", "password": "password"})
        self.assertContains(response, '<p class="errornote">')
        
    def testCache(self):
        log = []
        self.assertEqual(CachedRemoteResource.objects.count(), 0)
        # Send the first request, which is uncached.
        response_1 = remote.open(OK_URL, cache=True, prefetch=True, log=log)
        self.assertEqual(CachedRemoteResource.objects.count(), 1)
        self.assertEqual(len(log), 1)
        # Send the second request, which should be cached.
        response_2 = remote.open(OK_URL, cache=True, prefetch=True, log=log)
        self.assertEqual(CachedRemoteResource.objects.count(), 1)
        self.assertEqual(len(log), 1)
        self.assertEqual(response_1.content, response_2.content)
        # Hack the cache to force a reload.
        cached_resource = CachedRemoteResource.objects.get()
        cached_resource.timestamp = datetime.datetime(1985, 6, 30)  # Jenny's birthday!
        cached_resource.save()
        response_3 = remote.open(OK_URL, cache=True, prefetch=True, log=log)
        self.assertEqual(CachedRemoteResource.objects.count(), 1)
        self.assertEqual(len(log), 2)
        self.assertEqual(response_2.content, response_3.content)
        # Hack the cache to force a reload, then use prefetch to satisfy it.
        cached_resource = CachedRemoteResource.objects.get()
        cached_resource.timestamp = datetime.datetime(1984, 5, 19)  # My birthday!  Hint hint...
        cached_resource.save()
        remote.prefetch(log)
        self.assertEqual(len(log), 3)
        response_4 = remote.open(OK_URL, cache=True, prefetch=True, log=log)
        self.assertEqual(CachedRemoteResource.objects.count(), 1)
        self.assertEqual(len(log), 3)
        self.assertEqual(response_3.content, response_4.content)
        # Make sure that prefetch preloads all resources, regardless of expiry date.
        remote.prefetch(log)
        self.assertEqual(len(log), 4)
        # Hack the cache to expire the prefetch period, then make sure prefetch ignores the url.
        cached_resource = CachedRemoteResource.objects.get()
        cached_resource.prefetch_expires = datetime.datetime(1987, 4, 8)  # Rachael's birthday!
        cached_resource.save()
        remote.prefetch(log)
        self.assertEqual(len(log), 4)
        
    
XML_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<document>
    <section id="section-0">
        <title>Section 0</title>
    </section>
    <section id="section-1">
        <title>Section 1</title>
    </section>
    <section id="section-2">
        <title>Section 2</title>
    </section>
    <section id="section-3">
        <title>Section 3</title>
    </section>
</document>"""
        
        
class XMLTest(TestCase):
    
    """Tests that the XML library works."""
    
    def testLoadFile(self):
        """Tests that the XML parser can read files."""
        file = cStringIO.StringIO(XML_DATA)
        xml.parse(file)
    
    def testReadXML(self):
        """Test the various XML reading capabilities."""
        x = xml.parse(XML_DATA)
        # Read a single element.
        self.assertEqual(x.filter("title").value, "Section 0")
        self.assertEqual(x.filter("title")[1].value, "Section 1")
        # Iterate over multiple elements.
        for index, title in enumerate(x.filter("title")):
            # Ensure can read values.
            self.assertEqual(title.value, "Section %i" % index)
        # Iterate over child elements.
        for index, section in enumerate(x.children("section")):
            # Ensure can read attributes.
            self.assertEqual(section.attrs["id"], "section-%i" % index)
        # Ensure than children only includes direct descendents.
        # Ensure than length can be read.
        self.assertEqual(len(x.children("title")), 0)
    
    