import logging
import xml
from collections import defaultdict

import rdflib
import rdflib.parser
from rdflib.namespace import NamespaceManager, Namespace
from rdflib import URIRef
from rdflib.namespace import RDF

from ckanext.dcat.processors import RDFParserException

SHACL = Namespace("http://www.w3.org/ns/shacl#")

log = logging.getLogger(__name__)


class ShaclParser(object):

    def __init__(self, resultpath):
        self.g = rdflib.Graph()
        try:
            self.g.parse(resultpath, format='turtle')
        except (SyntaxError, xml.sax.SAXParseException,
                rdflib.plugin.PluginException, TypeError), e:

            raise RDFParserException(e)
        log.debug(
            "SHACL result graph parsed: length: {}"
            .format(len(self.g)))
        self.g.bind('sh', SHACL)
        self.g.namespace_manager = NamespaceManager(self.g)

    def errors_grouped_by_node(self):
        """parsing the shacl results"""
        error_dict_grouped_by_node = defaultdict(list)
        ref_processed_count = 0
        for result_ref in self.g.subjects(RDF.type, SHACL.ValidationResult):
            result_dict = self._shaclresult(result_ref)
            focusnode = self.g.value(result_ref, SHACL.focusNode)
            if isinstance(focusnode, URIRef):
                node = unicode(focusnode)
            else:
                node = ('catalog')
            try:
                value = ""
                if 'value' in result_dict:
                    value = ", Value: [{}]".format(
                        result_dict['value'].encode('utf-8'))
                message = """[{}]: {}: [{}]: '{}' {} ({})""".format(
                        node.encode('utf-8'),
                        result_dict.get('severity', ''),
                        result_dict.get('path', ''),
                        result_dict.get('message', '').encode('utf-8'),
                        value,
                        result_dict.get('constraint', '').encode('utf-8'))
            except UnicodeEncodeError as e:
                log.error("SHACL error for parsing results"
                          .format(e))
                raise
            else:
                error_dict_grouped_by_node[node].append(message)
            ref_processed_count += 1
        log.debug("SHACL: {} number of shacl results processed and grouped"
                  .format(ref_processed_count))
        return error_dict_grouped_by_node

    def _shaclresult(self, result_ref):
        """parsing a shacl result"""
        result_dict = {}
        for key, predicate in (
                ('message', SHACL.resultMessage),
                ('value', SHACL.value),
                ('path', SHACL.resultPath),
                ('detail', SHACL.resultDetail),
                ('severity', SHACL.resultSeverity),
                ('constraint', SHACL.sourceConstraintComponent),
        ):
            value = self._object_value(result_ref, predicate)
            if value:
                result_dict[key] = value
        return result_dict

    def _object_value(self, subject, predicate):
        """get the value of an object using the namespace"""
        o = self.g.value(subject, predicate)
        if isinstance(o, rdflib.Literal):
            return unicode(o)
        elif isinstance(o, rdflib.URIRef):
            return self.g.namespace_manager.qname(o)
        else:
            return None