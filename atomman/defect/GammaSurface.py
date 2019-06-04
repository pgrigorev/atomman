# Standard Python imports
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)
from collections import OrderedDict
import os

# http://pandas.pydata.org/
import pandas as pd

# http://www.numpy.org/
import numpy as np

# https://www.scipy.org/
from scipy.interpolate import griddata, Rbf, NearestNDInterpolator

# http://matplotlib.org/
import matplotlib.pyplot as plt

# https://github.com/usnistgov/DataModelDict
from DataModelDict import DataModelDict as DM

# atomman imports
from .. import Box
from .. import unitconvert as uc
from ..compatibility import stringtype

class GammaSurface(object):
    """
    Class for representing gamma surfaces, i.e., generalized stacking faults.
    """
    
    def __init__(self, model=None, a1vect=None, a2vect=None,
                 a1=None, a2=None, E_gsf=None, box=None, delta=None):
        """
        Class initializer. Parameter model must be given alone. Otherwise,
        all or none of a1vect, a2vect, a1, a2, and E_gsf must be given.
        
        Parameters
        ----------
        model : str, file-like object, DataModelDict, optional
            XML/JSON data model containing the stacking fault information.
        a1vect : array-like object, optional
            The a1 shifting vector.  If box is given, a1vect is taken as a
            crystal lattice vector, otherwise as a Cartesian vector.
        a2vect : array-like object, optional
            The a2 shifting vector.  If box is given, a2vect is taken as a
            crystal lattice vector, otherwise as a Cartesian vector.
        a1 : array-like object, optional
            List of fractional coordinates along a1vect corresponding to the
            E_gsf (and delta) values.
        a2 : array-like object, optional
            List of fractional coordinates along a2vect corresponding to the
            E_gsf (and delta) values.
        E_gsf : array-like object, optional
            List of generalized stacking fault energies for the positions
            associated with the corresponding (a1, a2) fractional coordinates.
        box : atomman.Box, optional
            Defines unit cell box dimensions for conversion between crystal
            lattice and Cartesian vectors.  If not given, will be set as a
            square unit box, thus no conversion will occur (i.e. a1vect,
            a2vect will be Cartesian).
        delta : array-like object, optional
            List of change in displacements normal to the fault plane for the
            positions associated with the corresponding (a1, a2) fractional
            coordinates.
        """
    
        # Load model if given
        if model is not None:
            try:
                assert box is None
                assert a1vect is None
                assert a2vect is None
                assert a1 is None
                assert a2 is None
                assert E_gsf is None
                assert delta is None
            except:
                raise TypeError('model cannot be given with any other parameter')
            else:
                self.model(model=model)
        
        # Set values if given
        elif (a1 is not None or a2 is not None or E_gsf is not None
              or a1vect is not None or a2vect is not None
              or delta is not None or box is not None):
            try:
                assert a1vect is not None
                assert a2vect is not None
                assert a1 is not None
                assert a2 is not None
                assert E_gsf is not None
            except:
                raise TypeError('Defining data requires a1vect, a2vect, a1, a2 and E_gsf')
            else:  
                self.set(a1vect, a2vect, a1, a2, E_gsf,  box=box, delta=delta)
        
        # Set flag for no supplied data
        else:
            self.__hasdata = False
    
    @property
    def data(self):
        """pandas.DataFrame : The raw data."""
        if self.__hasdata:
            return self.__data
        else:
            raise AttributeError('gamma surface data not set')
          
    @property
    def a1vect(self):
        """numpy.ndarray : The a1 shifting vector."""
        if self.__hasdata:
            return self.__a1vect
        else:
            raise AttributeError('gamma surface data not set')
    
    @property
    def a2vect(self):
        """numpy.ndarray : The a2 shifting vector."""
        if self.__hasdata:
            return self.__a2vect
        else:
            raise AttributeError('gamma surface data not set')
    
    @property
    def planenormal(self):
        """numpy.ndarray : The Cartesian vector normal to the fault plane."""
        if self.__hasdata:
            return self.__planenormal
        else:
            raise AttributeError('gamma surface data not set')

    @property
    def box(self):
        """
        atomman.Box : A unit cell box used for converting between
                      crystal lattice and Cartesian vectors.
        """
        if self.__hasdata:
            return self.__box
        else:
            raise AttributeError('gamma surface data not set')
    
    def set(self, a1vect, a2vect, a1, a2, E_gsf,  box=None, delta=None):
        """
        Sets generalized stacking fault data.
        
        Parameters
        ----------
        a1vect : array-like object
            The a1 shifting vector.  If box is given, a1vect is taken as a
            crystal lattice vector, otherwise as a Cartesian vector.
        a2vect : array-like object
            The a2 shifting vector.  If box is given, a2vect is taken as a
            crystal lattice vector, otherwise as a Cartesian vector.
        a1 : array-like object
            List of fractional coordinates along a1vect corresponding to the
            E_gsf (and delta) values.
        a2 : array-like object
            List of fractional coordinates along a2vect corresponding to the
            E_gsf (and delta) values.
        E_gsf : array-like object
            List of generalized stacking fault energies for the positions
            associated with the corresponding (a1, a2) fractional coordinates.
        box : atomman.Box, optional
            Defines unit cell box dimensions for conversion between crystal
            lattice and Cartesian vectors.  If not given, will be set as a
            square unit box, thus no conversion will occur (i.e. a1vect,
            a2vect will be Cartesian).
        delta : array-like object, optional
            List of change in displacements normal to the fault plane for the
            positions associated with the corresponding (a1, a2) fractional
            coordinates.
        """
        # Set a1vect
        if isinstance(a1vect, stringtype):
            a1vect = a1vect.split()
        a1vect = np.asarray(a1vect, dtype=float)
        if a1vect.shape != (3,):
            raise ValueError('a1vect must be a 3D vector')
        self.__a1vect = a1vect

        # Set a2vect
        if isinstance(a2vect, stringtype):
            a2vect = a2vect.split()
        a2vect = np.asarray(a2vect, dtype=float)
        if a2vect.shape != (3,):
            raise ValueError('a2vect must be a 3D vector')
        self.__a2vect = a2vect

        # Set box
        if box is None:
            box = Box()
        if not isinstance(box, Box):
            raise TypeError('box must be an atomman.Box')
        self.__box = box

        # Set plane normal
        a1vect = np.dot(a1vect, box.vects)
        a2vect = np.dot(a2vect, box.vects)
        self.__planenormal = np.cross(a1vect, a2vect)

        # Set data
        data = OrderedDict()
        data['a1'] = a1
        data['a2'] = a2
        data['E_gsf'] = E_gsf
        if delta is not None:
            data['delta'] = delta
        self.__data = pd.DataFrame(data)

        # Fit
        self.__hasdata = True
        self.fit()        
    
    def fit(self):
        """
        Defines the interpolation functions from the raw data.
        """
        
        # Ignore a1, a2=1.0 values if included
        shortdata = self.data[~(np.isclose(self.data.a1, 1.0) | np.isclose(self.data.a2, 1.0))]
        
        # Create supercells of values
        a1 = shortdata.a1
        a2 = shortdata.a2
        a1 = np.concatenate([a1-1, a1-1, a1-1, a1, a1, a1, a1+1, a1+1, a1+1])
        a2 = np.concatenate([a2-1, a2, a2+1, a2-1, a2, a2+1, a2-1, a2, a2+1])

        # Find values in 0-1 cell +- one point
        ua1 = np.unique(a1)
        ua2 = np.unique(a2)
        a1min = ua1[np.where(np.isclose(ua1, 0.0))[0][0] - 1] - 1e-8
        a1max = ua1[np.where(np.isclose(ua1, 1.0))[0][-1] + 1] + 1e-8
        a2min = ua2[np.where(np.isclose(ua2, 0.0))[0][0] - 1] - 1e-8
        a2max = ua2[np.where(np.isclose(ua2, 1.0))[0][-1] + 1] + 1e-8
        ix = np.where((a1 >= a1min) & (a1 <= a1max) & (a2 >= a2min) & (a2 <= a2max))
        
        # Fit energy
        E_gsf = np.concatenate([shortdata.E_gsf] * 9)
        self.__E_gsf_fit = Rbf(a1[ix], a2[ix], E_gsf[ix])
        self.__E_gsf_nearest = NearestNDInterpolator(np.array([a1[ix], a2[ix]]).T, E_gsf[ix])
        
        # Fit delta
        if 'delta' in self.data:
            delta = np.concatenate([shortdata.delta] * 9)
            self.__delta_fit = Rbf(a1[ix], a2[ix], delta[ix])
            self.__delta_nearest = NearestNDInterpolator(np.array([a1[ix], a2[ix]]).T, delta[ix])
    
    def model(self, model=None, length_unit='angstrom',
              energyperarea_unit='eV/angstrom^2'):
        """
        Return or set DataModelDict representation of the gamma surface.
        
        Parameters
        ----------
        model : str, file-like object or DataModelDict, optional
            XML/JSON content to extract gamma surface energy from. If not
            given, model content will be generated.
        length_unit : str, optional
            Units to report delta displacement values in when a new model is
            generated. Default value is 'angstrom'.
        energyperarea_unit : str, optional
            Units to report fault energy values in when a new model is
            generated.  Default value is 'mJ/m^2'.
        
        Returns
        -------
        DataModelDict
            A dictionary containing the stacking fault data of the
            GammaSurface object.  Returned if model is not given.
        """
        # Set values if model given
        if model is not None:
            model = DM(model).find('stacking-fault-map')
            
            # Read in box, a1vect and a2vect
            box = Box(avect = model['box']['avect'],
                      bvect = model['box']['bvect'],
                      cvect = model['box']['cvect'])
            
            a1vect = model['shift-vector-1']
            a2vect = model['shift-vector-2']
            
            # Read in stacking fault data
            gsf = model.find('stacking-fault-relation')
            
            a1 = gsf['shift-vector-1-fraction']
            a2 = gsf['shift-vector-2-fraction']
            E_gsf = uc.value_unit(gsf['energy'])
            try:
                delta = uc.value_unit(gsf['plane-separation'])
            except:
                delta = None
            self.set(a1vect, a2vect, a1, a2, E_gsf, box=box, delta=delta)
        
        # Generate model
        else:
            model = DM()
            model['stacking-fault-map'] = sfm = DM()
            sfm['box'] = DM()
            sfm['box']['avect'] = list(self.box.avect)
            sfm['box']['bvect'] = list(self.box.bvect)
            sfm['box']['cvect'] = list(self.box.cvect)
            sfm['shift-vector-1'] = list(self.a1vect)
            sfm['shift-vector-2'] = list(self.a2vect)
            sfm['stacking-fault-relation'] = sfr = DM()
            sfr['shift-vector-1-fraction'] = list(self.data.a1)
            sfr['shift-vector-2-fraction'] = list(self.data.a2)
            sfr['energy'] = uc.model(self.data.E_gsf, energyperarea_unit)
            if 'delta' in self.data:
                sfr['plane-separation'] = uc.model(self.data.delta, length_unit)
            
            return model
    
    def a12_to_pos(self, a1, a2, a1vect=None, a2vect=None):
        """
        Conversion function from normalized a1, a2 coordinates to Cartesian
        positions.
        
        Parameters
        ----------
        a1 : float(s)
            Fractional distance(s) along a1 vector.
        a2 : float(s)
            Fractional distance(s) along a2 vector.
        a1vect : np.array, optional
            Crystal vector for the a1 vector.  Default value of None uses the
            saved a1vect.
        a2vect : np.array, optional
            Crystal vector for the a2 vector.  Default value of None uses the
            saved a2vect.
        
        Returns
        -------
        np.array
            3D Cartesian position vector(s).
        """
        # Handle a1vect and a2vect
        if a1vect is None:
            a1vect = self.a1vect
        a1vect = np.asarray(a1vect)

        if a2vect is None:
            a2vect = self.a2vect
        a2vect = np.asarray(a2vect)
        
        # Convert a1vect and a2vect from crystal to Cartesian coordinates
        a1vect = np.dot(a1vect, self.box.vects)
        a2vect = np.dot(a2vect, self.box.vects)
        
        # Transform a1, a2 to Cartesian pos
        return np.outer(a1, a1vect) + np.outer(a2, a2vect)
        
    def pos_to_xy(self, pos, xvect=None):
        """
        Conversion function from Cartesian positions to plotting x, y
        coordinates.
        
        Parameters
        ----------
        pos: np.array
            3D Cartesian position vector(s).
        xvect : np.array, optional
            Cartesian vector corresponding to the plotting x-axis. If None (default), this is
            taken as the Cartesian of a1vect.
        
        Returns
        -------
        x : float(s)
            Plotting x coordinate(s).
        y : float(s)
            Plotting y coordinate(s).
        """
        # Handle xvect
        if xvect is None:
            xvect = np.dot(self.a1vect, self.box.vects)
        xvect = np.asarray(xvect)        
        if not np.isclose(np.dot(xvect, self.planenormal), 0.0):
            raise ValueError('xvect must be in plane defined by a1vect and a2vect')
        
        # Build transformation tensor
        yvect = np.cross(self.planenormal, xvect)
        transform = np.array([xvect, yvect, self.planenormal])
        transform = (transform.T / np.linalg.norm(transform, axis=1)).T
        
        # Transform coordinates to x,y,z orientation
        pos = transform.dot(pos.T).T
        
        # Return x, y coordinates
        return pos[...,0], pos[...,1]
    
    def a12_to_xy(self, a1, a2, a1vect=None, a2vect=None, xvect=None):
        """
        Conversion function from normalized a1, a2 coordinates to plotting x, y
        coordinates.
        
        Parameters
        ----------
        a1 : float(s)
            Fractional distance(s) along a1 vector.
        a2 : float(s)
            Fractional distance(s) along a2 vector.
        a1vect : np.array, optional
            Crystal vector for the a1 vector.  Default value of None uses the
            saved a1vect.
        a2vect : np.array, optional
            Crystal vector for the a2 vector.  Default value of None uses the
            saved a2vect.
        xvect : np.array, optional
            Cartesian vector corresponding to the plotting x-axis. If None (default), this is
            taken as the Cartesian of a1vect.
        
        Returns
        -------
        x : float(s)
            Plotting x coordinate(s).
        y : float(s)
            Plotting y coordinate(s).
        """
        # Set xvect as given a1vect if needed
        if a1vect is not None and xvect is None:
            xvect = np.dot(a1vect, self.box.vects)
        
        # Transform from a1, a2 to pos
        pos = self.a12_to_pos(a1, a2, a1vect=a1vect, a2vect=a2vect)

        # Transform from pos to x, y
        return self.pos_to_xy(pos, xvect=xvect)
    
    def pos_to_a12(self, pos, a1vect=None, a2vect=None):
        """
        Conversion function from Cartesian positions to normalized a1, a2
        coordinates.
        
        Parameters
        ----------
        pos : np.array
            3D Cartesian position vector(s).
        a1vect : np.array, optional
            Crystal vector for the a1 vector.  Default value of None uses the
            saved a1vect.
        a2vect : np.array, optional
            Crystal vector for the a2 vector.  Default value of None uses the
            saved a2vect.

        Returns
        -------
        a1 : float(s)
            Fractional distance(s) along a1 vector.
        a2 : float(s)
            Fractional distance(s) along a2 vector.
        """

        # Handle a1vect and a2vect
        if a1vect is None:
            a1vect = self.a1vect
        a1vect = np.asarray(a1vect)

        if a2vect is None:
            a2vect = self.a2vect
        a2vect = np.asarray(a2vect)
        
        # Convert a1vect and a2vect from crystal to Cartesian coordinates
        a1vect = np.dot(a1vect, self.box.vects)
        a2vect = np.dot(a2vect, self.box.vects)
        
        # Solve for a1, a2, a3
        a3vect = np.cross(a1vect, a2vect)
        coeffs = np.array([np.array([a1vect, a2vect, a3vect]).T])
        a123 = np.linalg.solve(coeffs, pos)
        assert np.allclose(a123[...,2], 0.0, atol=1e-6), np.abs(a123[...,2]).max()

        # Return a1, a2
        return a123[...,0], a123[...,1]
    
    def xy_to_pos(self, x, y, xvect=None):
        """
        Conversion function from plotting x, y coordinates to Cartesian
        positions.
        
        Parameters
        ----------
        x : float(s)
            Plotting x coordinate(s).
        y : float(s)
            Plotting y coordinate(s).
        xvect : np.array, optional
            Cartesian vector corresponding to the plotting x-axis. If None
            (default), this is taken as the Cartesian of a1vect.
        
        Returns
        -------
        pos: np.array
            3D Cartesian position vector(s).
        """
        # Assign default xvect if needed
        if xvect is None:
            xvect = np.dot(self.a1vect, self.box.vects)
        xvect = np.asarray(xvect)
        if not np.isclose(np.dot(xvect, self.planenormal), 0.0):
            raise ValueError('xvect must be in plane defined by a1vect and a2vect')
       
        # Build transformation tensor
        yvect = np.cross(self.planenormal, xvect)
        transform = np.array([xvect, yvect, self.planenormal])
        transform = (transform.T / np.linalg.norm(transform, axis=1)).T
        transform = np.linalg.inv(transform)
        
        # Transform coords
        pos = np.outer(x, [1,0,0]) + np.outer(y, [0,1,0])
        pos = transform.dot(pos.T).T
        
        # Return Cartesian pos
        return pos
    
    def xy_to_a12(self, x, y, a1vect=None, a2vect=None, xvect=None):
        """
        Conversion function from plotting x, y coordinates to normalized a1, a2
        coordinates.
        
        Parameters
        ----------
        x : float(s)
            Plotting x coordinate(s).
        y : float(s)
            Plotting y coordinate(s).
        a1vect : np.array, optional
            Crystal vector for the a1 vector.  Default value of None uses the
            saved a1vect.
        a2vect : np.array, optional
            Crystal vector for the a2 vector.  Default value of None uses the
            saved a2vect.
        xvect : np.array, optional
            Cartesian vector corresponding to the plotting x-axis. If None
            (default), this is taken as the Cartesian of a1vect.
        
        Returns
        -------
        a1 : float(s)
            Fractional distance(s) along a1 vector.
        a2 : float(s)
            Fractional distance(s) along a2 vector.
        """
        
        # Set xvect to given a1vect if needed
        if a1vect is not None and xvect is None:
            xvect = np.dot(a1vect, self.box.vects)

        # Convert x, y to pos    
        pos = self.xy_to_pos(x, y, xvect=xvect)

        # Convert pos to a1, a2
        return self.pos_to_a12(pos, a1vect=a1vect, a2vect=a2vect)
    
    def E_gsf(self, **kwargs):
        """
        Returns values for generalized stacking fault energy interpolated from
        the raw data.  Values can be obtained relative to a1, a2 fractional
        coordinates, x, y plotting coordinates, or pos Cartesian coordinates.
        
        Parameters
        ----------
        a1 : float(s), optional
            Fractional coordinate(s) along a1vect.
        a2 : float(s), optional
            Fractional coordinate(s) along a2vect.
        pos : np.array, optional
            3D Cartesian position vector(s).
        x : float(s), optional
            Plotting x coordinate(s).
        y : float(s), optional
            Plotting y coordinate(s).
        a1vect : np.array, optional
            Vector for the a1 fractional coordinates.  Default value of None 
            uses the saved a1vect.
        a2vect : np.array, optional
            Vector for the a2 fractional coordinates.  Default value of None 
            uses the saved a2vect.
        xvect : np.array, optional
            Cartesian vector corresponding to the plotting x-axis. If None
            (default), this is taken as the Cartesian of a1vect.
        smooth : bool, optional
            If True (default) the returned values are smoothed using a RBF fit.
            If False, the closest measured values are returned.
        """
        if not self.__hasdata:
            raise AttributeError('gamma surface data not set')
        
        smooth = kwargs.pop('smooth', True)

        # Convert x, y to a1, a2
        if 'x' in kwargs:
            x = kwargs.pop('x')
            y = kwargs.pop('y')
            a1vect = kwargs.pop('a1vect', None)
            a2vect = kwargs.pop('a2vect', None)
            xvect = kwargs.pop('xvect', None)
            assert len(kwargs) == 0, 'Unknown/incompatible arguments given'
            a1, a2 = self.xy_to_a12(x, y, a1vect=a1vect, a2vect=a2vect, xvect=xvect)
        
        # Convert pos to a1, a2
        elif 'pos' in kwargs:
            pos = kwargs.pop('pos')
            a1vect = kwargs.pop('a1vect', None)
            a2vect = kwargs.pop('a2vect', None)
            assert len(kwargs) == 0, 'Unknown/incompatible arguments given'
            a1, a2 = self.pos_to_a12(pos, a1vect=a1vect, a2vect=a2vect)
        
        # Get a1, a2 from kwargs
        else:
            a1 = np.array(kwargs.pop('a1'))
            a2 = np.array(kwargs.pop('a2'))
            a1vect = kwargs.pop('a1vect', None)
            a2vect = kwargs.pop('a2vect', None)
            assert len(kwargs) == 0, 'Unknown/incompatible arguments given'
            if a1vect is not None or a2vect is not None:
                shape = a1.shape               
                # Convert into pos using given a1vect, a2vect, then back into a1, a2
                pos = self.a12_to_pos(a1, a2, a1vect=a1vect, a2vect=a2vect)
                a1, a2 = self.pos_to_a12(pos)
                a1 = a1.reshape(shape)
                a2 = a2.reshape(shape)
        
        # Wrap all values within 0.0 < a1, a2 < 1.0
        while np.any(a1 > 1.0): 
            a1[a1 > 1.0] -= 1.0
        while np.any(a1 < 0.0): 
            a1[a1 < 0.0] += 1.0
        while np.any(a2 > 1.0): 
            a2[a2 > 1.0] -= 1.0
        while np.any(a2 < 0.0): 
            a2[a2 < 0.0] += 1.0
        
        if smooth:
            return self.__E_gsf_fit(a1, a2)
        else:
            return self.__E_gsf_nearest(np.array([a1.flatten(), a2.flatten()]).T).reshape(a1.shape)
    
    def delta(self, **kwargs):
        """
        Returns values for generalized stacking fault energy interpolated from
        the raw data.  Values can be obtained relative to a1, a2 fractional
        coordinates, x, y plotting coordinates, or pos Cartesian coordinates.
        
        Parameters
        ----------
        a1 : float(s), optional
            Fractional coordinate(s) along a1vect.
        a2 : float(s), optional
            Fractional coordinate(s) along a2vect.
        pos : np.array, optional
            3D Cartesian position vector(s).
        x : float(s), optional
            Plotting x coordinate(s).
        y : float(s), optional
            Plotting y coordinate(s).
        a1vect : np.array, optional
            Vector for the a1 fractional coordinates.  Default value of None 
            uses the saved a1vect.
        a2vect : np.array, optional
            Vector for the a2 fractional coordinates.  Default value of None 
            uses the saved a2vect.
        xvect : np.array, optional
            Cartesian vector corresponding to the plotting x-axis. If None
            (default), this is taken as the Cartesian of a1vect.
        smooth : bool, optional
            If True (default) the returned values are smoothed using a RBF fit.
            If False, the closest measured values are returned.
        """
        if not self.__hasdata:
            raise AttributeError('gamma surface data not set')
        if 'delta' not in self.data:
            raise AttributeError('delta data not set')
        
        smooth = kwargs.pop('smooth', True)

        # Convert x, y to a1, a2
        if 'x' in kwargs:
            x = kwargs.pop('x')
            y = kwargs.pop('y')
            a1vect = kwargs.pop('a1vect', None)
            a2vect = kwargs.pop('a2vect', None)
            xvect = kwargs.pop('xvect', None)
            assert len(kwargs) == 0, 'Unknown/incompatible arguments given'
            a1, a2 = self.xy_to_a12(x, y, a1vect=a1vect, a2vect=a2vect, xvect=xvect)
        
        # Convert pos to a1, a2
        elif 'pos' in kwargs:
            pos = kwargs.pop('pos')
            a1vect = kwargs.pop('a1vect', None)
            a2vect = kwargs.pop('a2vect', None)
            assert len(kwargs) == 0, 'Unknown/incompatible arguments given'
            a1, a2 = self.pos_to_a12(pos, a1vect=a1vect, a2vect=a2vect)
        
        # Get a1, a2 from kwargs
        else:
            a1 = np.array(kwargs.pop('a1'))
            a2 = np.array(kwargs.pop('a2'))
            a1vect = kwargs.pop('a1vect', None)
            a2vect = kwargs.pop('a2vect', None)
            assert len(kwargs) == 0, 'Unknown/incompatible arguments given'
            if a1vect is not None or a2vect is not None:
                shape = a1.shape               
                # Convert into pos using given a1vect, a2vect, then back into a1, a2
                pos = self.a12_to_pos(a1, a2, a1vect=a1vect, a2vect=a2vect)
                a1, a2 = self.pos_to_a12(pos)
                a1 = a1.reshape(shape)
                a2 = a2.reshape(shape)
        
        # Wrap all values within 0.0 < a1, a2 < 1.0
        while np.any(a1 > 1.0): 
            a1[a1 > 1.0] -= 1.0
        while np.any(a1 < 0.0): 
            a1[a1 < 0.0] += 1.0
        while np.any(a2 > 1.0): 
            a2[a2 > 1.0] -= 1.0
        while np.any(a2 < 0.0): 
            a2[a2 < 0.0] += 1.0
        
        if smooth:
            return self.__delta_fit(a1, a2)
        else:
            return self.__delta_nearest(np.array([a1.flatten(), a2.flatten()]).T).reshape(a1.shape)
    
    def E_gsf_surface_plot(self, normalize=False, smooth=True, 
                           a1vect=None, a2vect=None, xvect=None,
                           length_unit='angstrom', energyperarea_unit='eV/angstrom^2',
                           numx=100, numy=100, figsize=None, **kwargs):
        """
        Creates a 2D surface plot from the stacking fault energy values.
        
        Parameters
        ----------
        normalize : bool, optional
            Flag indicating if axes are Cartesian (False, default) or
            normalized by a1, a2 vectors (True).
        smooth : bool, optional
            If True (default), then plot shows smooth interpolated values.
            If False, plot shows nearest raw data values.
        a1vect : np.array, optional
            Crystal vector for the a1 vector to use for plotting.  Default
            value of None uses the saved a1vect.
        a2vect : np.array, optional
            Crystal vector for the a2 vector to use for plotting.  Default
            value of None uses the saved a2vect.
        xvect : numpy.array, optional
            Crystal vector to align with the plotting x-axis for 
            non-normalized plots.  If not given, this is taken as the Cartesian
            of a1vect.
        length_unit : str, optional
            The unit of length to display non-normalized axes values in.
            Default value is 'angstrom'.
        energyperarea_unit : str, optional
            The unit of energy per area to display the stacking fault energies
            in. Default value is 'eV/angstrom^2'.
        numx : int, optional
            The number of plotting points to use along the x-axis.  Default
            value is 100.
        numy : int, optional
            The number of plotting points to use along the y-axis.  Default
            value is 100.       
        figsize : tuple or None, optional
            The figure's x,y dimensions.  If None (default), the values are
            scaled such that the x,y spacings are approximately equal, and the
            larger of the two values is set to 10.
        **kwargs : dict, optional
            Additional keywords are passed into the underlying 
            matplotlib.pyplot.pcolormesh(). This allows control of such things
            like the colormap (cmap).
            
        Returns
        -------
        matplotlib.figure
        """
        if not self.__hasdata:
            raise AttributeError('gamma surface data not set')

        # Extract data
        if a1vect is None:
            a1vect = self.a1vect
        a1vect = np.asarray(a1vect)
        if a2vect is None:
            a2vect = self.a2vect
        a2vect = np.asarray(a2vect)

        # Generate grids of a1, a2 values from numx, numy
        x_grid, y_grid = np.meshgrid(np.linspace(0, 1, numx),
                                     np.linspace(0, 1, numy))
        
        # Generate grid of values either with or without interpolation
        C = self.E_gsf(a1=x_grid, a2=y_grid, a1vect=a1vect, a2vect=a2vect, smooth=smooth)
        
        # Convert units of C using energyperarea_unit
        C = uc.get_in_units(C, energyperarea_unit)
        
        # Set parameters for normalized plots
        if normalize is True:
            yscale = 1
            xlabel = '$a_1$ = ' + str(a1vect)
            ylabel = '$a_2$ = ' + str(a2vect)
        
        # Set parameters for absolute plots
        else:
            shape = x_grid.shape
            x_grid, y_grid = self.a12_to_xy(x_grid.flatten(), y_grid.flatten(),
                                            a1vect=a1vect, a2vect=a2vect, xvect=xvect)
            x_grid.shape = shape
            y_grid.shape = shape
            x_grid = uc.get_in_units(x_grid, length_unit)
            y_grid = uc.get_in_units(y_grid, length_unit)
            yscale = (y_grid.max()-y_grid.min()) / (x_grid.max() - x_grid.min())
            xlabel = 'x (' + length_unit + ')'
            ylabel = 'y (' + length_unit + ')'
        
        # Set default figsize if needed
        if figsize is None:
            xscale = 1.175
            if yscale < 1:
                figsize = (xscale * 10, 10 * yscale)
            else:
                figsize = (xscale * 10 / yscale, 10)
        
        # Generate plot
        fig = plt.figure(figsize=figsize)
        plt.pcolormesh(x_grid, y_grid, C, **kwargs)
        plt.xlabel(xlabel, fontsize='x-large')
        plt.ylabel(ylabel, fontsize='x-large')
        cbar = plt.colorbar(aspect=40, fraction=0.1)
        cbar.ax.set_ylabel('$E_{gsf}$ (' + energyperarea_unit + ')',
                           fontsize='x-large')
        
        return fig
    
    def E_gsf_line_plot(self, vect=None, num=None, smooth=True,
                        length_unit='angstrom', energyperarea_unit='eV/angstrom^2',
                        figsize=None, fig=None, **kwargs):
        """
        Generates a line plot for the interpolated generalized stacking fault
        energy along a specified crystallographic vector in the (a1, a2) plane.
        
        Parameters
        ----------
        vect : numpy.array, optional
            Vector to plot the gsf along.  If box is set, this vect will be a
            lattice vector, otherwise it will be a Cartesian vector.  Must be 
            in the plane defined by the GammaSurface object's a1vect and 
            a2vect vectors.  Default value will use the set a1vect.
        num : int, optional
            The number of points to evaluate the generalized stacking fault
            energy for.  Default value is 100 if smooth is True, otherwise is
            number of unique a1 values from 0 to 1.
        smooth : bool, optional
            If True (default), then plot shows smooth interpolated values.
            If False, plot shows nearest raw data values.
        length_unit : str, optional
            The unit of length to display the x-axis coordinates in.
            Default value is 'angstrom'.
        energyperarea_unit : str, optional
            The unit of energy per area to display the stacking fault energies
            in. Default value is 'eV/angstrom^2'.
        figsize : tuple, optional
            The x,y size of the figure to return.  Default value is (10, 6).
        fig : matplotlib.figure, optional
            An existing figure object to add the new plot to.  If not given, a
            new figure is generated.
        **kwargs : dict, optional
            Additional keywords are passed into the underlying 
            matplotlib.pyplot.plot(). This allows control of such things
            like line color, style, etc.
        
        Returns
        -------
        matplotlib.figure
        """
        if not self.__hasdata:
            raise AttributeError('gamma surface data not set')

        if num is None:
            if smooth:
                num = 100
            else:
                unique_a1 = np.unique([self.data.a1 - 1, self.data.a1, self.data.a1 + 1])
                num = len(unique_a1[(unique_a1 >=-0.000001) & (unique_a1 <=1.000001)])
        
        # Generate coordinates
        a1 = np.linspace(0, 1, num)
        a2 = np.zeros(num)
        pos = self.a12_to_pos(a1, a2, a1vect=vect)
        
        # Evaluate interpolated energy and distance along x
        E = uc.get_in_units(self.E_gsf(pos=pos, smooth=smooth), energyperarea_unit)
        x = uc.get_in_units(np.linalg.norm(pos, axis=1), length_unit)
        
        # Create plot
        xmax = x.max()
        emin = E.min()
        emax = E.max()
        if fig is None:
            if figsize is None:
                figsize = (10, 6)
            fig = plt.figure(figsize=figsize)
        else:
            old_xmax = fig.axes[0].get_xlim()[-1]
            old_emin = fig.axes[0].get_ylim()[0]
            old_emax = fig.axes[0].get_ylim()[-1]
            if old_xmax > xmax:
                xmax = old_xmax
            if old_emin < emin:
                emin = old_emin
            if old_emax > emax:
                emax = old_emax
        if 'fmt' in kwargs:
            fmt = kwargs.pop('fmt')      
            plt.plot(x, E, fmt, **kwargs)
        else:
            plt.plot(x, E, **kwargs)
        
        if vect is None:
            vect = self.a1vect

        plt.xlabel('$x$ along ' + str(vect) + ' (' + str(length_unit) + ')',
                   fontsize='x-large')
        plt.ylabel('$E_{gsf}$ (' + str(energyperarea_unit) + ')', fontsize='x-large')
        plt.xlim(0, xmax)
        plt.ylim(emin, emax)
        
        return fig
    
    def delta_surface_plot(self, normalize=False, smooth=True, 
                           a1vect=None, a2vect=None, xvect=None,
                           length_unit='angstrom',
                           numx=100, numy=100, figsize=None, **kwargs):
        """
        Creates a 2D surface plot from the delta planar displacement values.
        
        Parameters
        ----------
        normalize : bool, optional
            Flag indicating if axes are Cartesian (False, default) or
            normalized by a1, a2 vectors (True).
        smooth : bool, optional
            If True (default), then plot shows smooth interpolated values.
            If False, plot shows nearest raw data values.
        a1vect : np.array, optional
            Crystal vector for the a1 vector to use for plotting.  Default
            value of None uses the saved a1vect.
        a2vect : np.array, optional
            Crystal vector for the a2 vector to use for plotting.  Default
            value of None uses the saved a2vect.
        xvect : numpy.array, optional
            Crystal vector to align with the plotting x-axis for 
            non-normalized plots.  If not given, this is taken as the Cartesian
            of a1vect.
        length_unit : str, optional
            The unit of length to display delta and non-normalized axes values
            in.  Default value is 'angstrom'.
        numx : int, optional
            The number of plotting points to use along the x-axis.  Default
            value is 100.
        numy : int, optional
            The number of plotting points to use along the y-axis.  Default
            value is 100.       
        figsize : tuple or None, optional
            The figure's x,y dimensions.  If None (default), the values are
            scaled such that the x,y spacings are approximately equal, and the
            larger of the two values is set to 10.
        **kwargs : dict, optional
            Additional keywords are passed into the underlying 
            matplotlib.pyplot.pcolormesh(). This allows control of such things
            like the colormap (cmap).
            
        Returns
        -------
        matplotlib.figure
        """
        if not self.__hasdata:
            raise AttributeError('gamma surface data not set')
        if 'delta' not in self.data:
            raise AttributeError('delta data not set')

        # Extract data
        if a1vect is None:
            a1vect = self.a1vect
        a1vect = np.asarray(a1vect)
        if a2vect is None:
            a2vect = self.a2vect
        a2vect = np.asarray(a2vect)

        # Generate grids of a1, a2 values from numx, numy
        x_grid, y_grid = np.meshgrid(np.linspace(0, 1, numx),
                                     np.linspace(0, 1, numy))
        
        # Generate grid of values either with or without interpolation
        C = self.delta(a1=x_grid, a2=y_grid, a1vect=a1vect, a2vect=a2vect, smooth=smooth)
        
        # Convert units of C using length_unit
        C = uc.get_in_units(C, length_unit)
        
        # Set parameters for normalized plots
        if normalize is True:
            yscale = 1
            xlabel = '$a_1$ = ' + str(a1vect)
            ylabel = '$a_2$ = ' + str(a2vect)
        
        # Set parameters for absolute plots
        else:
            shape = x_grid.shape
            x_grid, y_grid = self.a12_to_xy(x_grid.flatten(), y_grid.flatten(),
                                            a1vect=a1vect, a2vect=a2vect, xvect=xvect)
            x_grid.shape = shape
            y_grid.shape = shape
            x_grid = uc.get_in_units(x_grid, length_unit)
            y_grid = uc.get_in_units(y_grid, length_unit)
            yscale = (y_grid.max()-y_grid.min()) / (x_grid.max() - x_grid.min())
            xlabel = 'x (' + length_unit + ')'
            ylabel = 'y (' + length_unit + ')'
        
        # Set default figsize if needed
        if figsize is None:
            xscale = 1.175
            if yscale < 1:
                figsize = (xscale * 10, 10 * yscale)
            else:
                figsize = (xscale * 10 / yscale, 10)
        
        # Generate plot
        fig = plt.figure(figsize=figsize)
        plt.pcolormesh(x_grid, y_grid, C, **kwargs)
        plt.xlabel(xlabel, fontsize='x-large')
        plt.ylabel(ylabel, fontsize='x-large')
        cbar = plt.colorbar(aspect=40, fraction=0.1)
        cbar.ax.set_ylabel('$\delta_{gsf}$ (' + length_unit + ')',
                           fontsize='x-large')
        
        return fig
    
    def delta_line_plot(self, vect=None, num=None, smooth=True,
                        length_unit='angstrom',
                        figsize=None, fig=None, **kwargs):
        """
        Generates a line plot for the interpolated delta planar shift values
        along a specified crystallographic vector in the (a1, a2) plane.
        
        Parameters
        ----------
        vect : numpy.array, optional
            Vector to plot the gsf along.  If box is set, this vect will be a
            lattice vector, otherwise it will be a Cartesian vector.  Must be 
            in the plane defined by the GammaSurface object's a1vect and 
            a2vect vectors.  Default value will use the set a1vect.
        num : int, optional
            The number of points to evaluate the generalized stacking fault
            energy for.  Default value is 100 if smooth is True, otherwise is
            number of unique a1 values from 0 to 1.
        smooth : bool, optional
            If True (default), then plot shows smooth interpolated values.
            If False, plot shows nearest raw data values.
        length_unit : str, optional
            The unit of length to display the x-axis coordinates in.
            Default value is 'angstrom'.
        figsize : tuple, optional
            The x,y size of the figure to return.  Default value is (10, 6).
        fig : matplotlib.figure, optional
            An existing figure object to add the new plot to.  If not given, a
            new figure is generated.
        **kwargs : dict, optional
            Additional keywords are passed into the underlying 
            matplotlib.pyplot.plot(). This allows control of such things
            like line color, style, etc.
        
        Returns
        -------
        matplotlib.figure
        """
        if not self.__hasdata:
            raise AttributeError('gamma surface data not set')
        if 'delta' not in self.data:
            raise AttributeError('delta data not set')

        if num is None:
            if smooth:
                num = 100
            else:
                unique_a1 = np.unique([self.data.a1-1, self.data.a1, self.data.a1+1])
                num = len(unique_a1[(unique_a1 >=-0.000001) & (unique_a1 <=1.000001)])

        # Generate coordinates
        a1 = np.linspace(0, 1, num)
        a2 = np.zeros(num)
        pos = self.a12_to_pos(a1, a2, a1vect=vect)
        
        # Evaluate interpolated energy and distance along x
        E = uc.get_in_units(self.delta(pos=pos, smooth=smooth), length_unit)
        x = uc.get_in_units(np.linalg.norm(pos, axis=1), length_unit)
        
        # Create plot
        xmax = x.max()
        emin = E.min()
        if fig is None:
            if figsize is None:
                figsize = (10, 6)
            fig = plt.figure(figsize=figsize)
        else:
            old_xmax = fig.axes[0].get_xlim()[-1]
            old_emin = fig.axes[0].get_ylim()[0]
            if old_xmax > xmax:
                xmax = old_xmax
            if old_emin < emin:
                emin = old_emin
        if 'fmt' in kwargs:
            fmt = kwargs.pop('fmt')      
            plt.plot(x, E, fmt, **kwargs)
        else:
            plt.plot(x, E, **kwargs)
        
        if vect is None:
            vect = self.a1vect

        plt.xlabel('$x$ along ' + str(vect) + ' (' + length_unit + ')',
                   fontsize='x-large')
        plt.ylabel('$\delta_{gsf}$ (' + length_unit + ')', fontsize='x-large')
        plt.xlim(0, xmax)
        plt.ylim(emin, None)
        
        return fig