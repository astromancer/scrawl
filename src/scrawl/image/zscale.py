import numpy as np
from scipy.optimize import leastsq


class Zscale:
    """
    Class that implements the IRAF zscale algorithm to determine colour 
    limits for displaying astronomical images
    """
    def __init__(self, **kw):
    
        self.count = 0
        self.rejects = 0
        #self.data               = np.asarray( data )
        self.sigma_clip = kw.get('sigma_clip', 3.5)
        self.maxiter = kw.get('maxiter', 10)
        self.Npix = kw.get('Npix', 1000)
        self.min_pix = kw.get('min_pix', 100)
        self.max_pix_frac = kw.get('max_pix_frac', 0.5)
        self.mask = kw.get('mask')

    def apply_mask(self, data):
        """Apply bad pixel mask if given. Return flattened array"""
        if self.mask is None:
            return data.ravel()

        assert data.shape == self.mask.shape, 'Mask and data have unequal shapes.'
        return data[self.mask]

    def resample(self, data):
        """Resample data without replacement."""
        Npix = self.Npix
        mfrac = self.max_pix_frac
        
        # use at least this many pixels
        Npix = max(Npix, self.min_pix)  
        if Npix > data.size*mfrac:
            Npix = int(data.size*mfrac)  # use at most half of the image pixels

        return np.random.choice(data, size=Npix, replace=False)

    # TODO: memoize?
    def range(self, data, **kw):
        """
        Algorithm to determine colour limits for astronomical images based on 
        zscale algorithm used by IRAF display task.
        """
        # if data is None:
        #data = self.data
        if self.count == 0:
            # remove bad pixels and flatten
            data = self.apply_mask(data)
            # save range and size of original resampled data
            self.original_data_range = np.min(data), np.max(data)
            self.original_data_size = data.size
            # resample and sort ascending
            data = np.sort(self.resample(data), axis=None)

        Il = len(data)
        Ir = np.arange(Il)
        Im = np.median(data)

        # fit a straight line to the resampled, sorted pixel values
        def line(p, data): 
            return (p[0]*Ir + p[1])
        
        def residuals(p, data): 
            return np.abs(data - line(p, data))
        
        # initial guess for slope / intercep
        # = data[-1]-data[0] #can speed this up since data are sorted
        m0 = np.ptp(data) / Il
        p0 = m0, 0
        fit, _ = leastsq(residuals, p0, data)

        # Assume residuals are normally distributed and clip values outside acceptable confidence interval
        res = residuals(fit, data)
        clipped = res > res.std() * self.sigma_clip

        if clipped.any() and self.count < self.maxiter:
            self.count += 1
            self.rejects += clipped.sum()
            #print('rejects: ', self.rejects )
            # if more than half the original datapoints are rejected return original data range
            if self.rejects > self.original_data_size//2:
                return self.original_data_range
            return self.range(data[~clipped], **kw)

        contrast = kw.get('contrast', 1./100)
        midpoint = Il/2
        slope = fit[0]
        z1 = Im + (slope/contrast)*(1.-midpoint)
        z2 = Im + (slope/contrast)*(Il-midpoint)
        # restrict colour limits to data limits
        self.z1 = max(self.original_data_range[0], z1)
        self.z2 = min(self.original_data_range[-1], z2)
        self.count = 0
        self.rejects = 0
        return self.z1, self.z2


def zrange(data, **kw):
    """
    Algorithm to determine colour limits for astronomical images based on zscale
    algorithm used by IRAF display task.
    """
    contrast = kw.pop('contrast', 1./100)
    # TODO: resolve multiple masks
    if np.ma.is_masked(data):
        # WARNING:  this overwrites any explicit provided mask
        kw['mask'] = data.mask

    return Zscale(**kw).range(data, contrast=contrast)
