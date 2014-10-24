import weakref
from neuron import h
from .neuron_object import NeuronObject
from .segment import Segment


class Section(NeuronObject):
    
    allsec = weakref.WeakValueDictionary()
        
    def __init__(self, name=None, **kwds):
        # In order to ensure that we can uniquely map each NEURON section to
        # a single Section instance, they must have unique names. Therefore,
        # we do not allow the user to set the name of the NEURON section.
        self._name = name
        
        # To ensure we can destroy this Secion on demand, we must know all of
        # the Segments that reference this Section.
        self._segments = weakref.WeakValueDictionary()
        NeuronObject.__init__(self)
        
        self._create(**kwds)
        
        secname = self.__nrnobj.name()
        assert secname not in Section.allsec
        Section.allsec[secname] = self

    def _create(self, **kwds):
        if '_nrnobj' in kwds:
            self.__nrnobj = kwds['_nrnobj']
        else:
            self.__nrnobj = h.Section()
        self.__secref = h.SectionRef(sec=self.__nrnobj)

    @property
    def name(self):
        """The name given to this section at initialization, or None if no name
        was provided.
        """
        return self._name

    @property
    def nseg(self):
        """The number of segments in the section.
        """
        return self.__nrnobj.nseg
    
    @nseg.setter
    def nseg(self, n):
        self._forget_segments()
        self.__nrnobj.nseg = n
        
    @property
    def parent(self):
        """The parent of this section.

        If the section has not yet been connected to any others, then the
        parent is None.
        
        See also
        --------
        Section.connect()
        Section.trueparent
        Section.root
        """
        if self.__secref.has_parent() == 0:
            return None
        else:
            return Section._get(self.__secref.parent)
        
    @property
    def trueparent(self):
        """The true parent of this section.
        
        The true parent is usually the same as the parent, except in the case 
        where the section is _effectively_ attached to its grandparent by
        connecting to the base of its parent. For example:
        
            root = Section()
            dend1 = Section()
            dend2 = Section()
            dend1.connect(root, 0.5, 0)
            dend2.connect(dend1, 0, 0)
            
            # topology looks like:
            # 
            #           --- dend1
            #  root ---|
            #           --- dend2
            #
            
            dend2.parent == dend1
            dend2.trueparent == root
        """
        if self.__secref.has_trueparent() == 0:
            return None
        else:
            return Section._get(self.__secref.trueparent)

    @property
    def root(self):
        """The root section of the tree connected to this section.
        """
        return Section._get(self.__secref.root)

    @property
    def nchild(self):
        """The number of child sections attached to this section.
        """
        return int(self.__secref.nchild())

    def child(self, i):
        """Return the ith child to this Section.
        
        Parameters
        ----------
        i : int
            The index of the child to return, where 0 <= i < self.nchild.
        """
        if i >= self.nchild:
            raise ValueError("Cannot get child %d; only %d children exist." %
                             (i, self.nchild))
        return Section._get(self.__secref.child[i])
    
    @property
    def children(self):
        """An iterator over all children to this section.
        """
        for i in range(self.nchild):
            yield self.child(i)

    def connect(self, parent, parentx=1, childend=0):
        """Connect this section to another.
        
        Parameters
        ----------
        parent : Section
            The parent Section to connect to.
        parentx : float
            The position (0.0 to 1.0) along *parent* where *self* should be
            connected.
        childend : 0 or 1
            The end of *self* that should be connected to *parent*.
        
        """
        self.__nrnobj.connect(parent.__nrnobj, parentx, childend)
        
    def insert(self, mech):
        # todo: create & return Mechanism instance
        self.__nrnobj.insert(mech)

    def __call__(self, x):
        """Return a Segment pointing to position x on this Section.
        """
        if x < 0 or x > 1:
            raise ValueError("x must be between 0 and 1.")
        if x not in self._segments:
            seg = Segment(_nrnobj=self.__nrnobj(x))
            self._segments[x] = seg
        return self._segments[x]
        
    @property
    def nodes(self):
        """An iterator over all locations along the section that are at the 
        edge of a segment.
        """
        for i in range(self.nseg + 1):
            x = i / float(self.nseg)
            yield self(x)

    @property
    def segments(self):
        """An iterator over all locations along the section that are at the
        center of a segment.
        """
        for i in range(self.nseg):
            x = (i + 0.5) / self.nseg
            yield self(x)

    def _forget_segments(self):
        # forget all Segments
        for seg in self._segments.values():
            seg._destroy()
        self._segments.clear()

    def _destroy(self):
        self._forget_segments()  # Segments keep their Section alive, even if
                                 # they no longer belong to the section!
        self.__secref = None
        n = len(list(h.allsec()))
        NeuronObject._destroy(self)
        assert len(list(h.allsec())) < n
    
    @classmethod
    def _get(cls, sec):
        """Return the Section instance corresponding to the given NEURON 
        section, or create a new one if needed.
        """
        name = sec.name()
        if name in Section.allsec:
            return Section.allsec[name]
        else:
            return Section(_nrnobj=sec)