import numpy as np
import logging
import time
from .base import BaseEnvironmentEstimator
from .src import minkowski as Mk


class MinkowskiFunctionals(BaseEnvironmentEstimator):
    """
    Class to compute the Minkowski functionals.
    """
    def __init__(self, **kwargs):

        self.logger = logging.getLogger('MinkowskiFunctionals')
        self.logger.info('Initializing MinkowskiFunctionals.')
        super().__init__(**kwargs)
        
    def set_density_contrast(self, smoothing_radius=None, check=False, ran_min=0.01, save_wisdom=False):
        """
        Set the density contrast.

        Parameters
        ----------
        smoothing_radius : float, optional
            Smoothing radius.
        check : bool, optional
            Check if there are enough randoms.
        ran_min : float, optional
            Minimum randoms.
        nquery_factor : int, optional
            Factor to multiply the number of data points to get the number of query points.
            
        Returns
        -------
        delta_mesh : array_like
            Density contrast.
        """
        t0 = time.time()
        if smoothing_radius:
            self.data_mesh.smooth_gaussian(smoothing_radius, engine='fftw', save_wisdom=save_wisdom,)
        if self.has_randoms:
            if check:
                mask_nonzero = self.randoms_mesh.value > 0.
                nnonzero = mask_nonzero.sum()
                if nnonzero < 2: raise ValueError('Very few randoms.')
            if smoothing_radius:
                self.randoms_mesh.smooth_gaussian(smoothing_radius, engine='fftw', save_wisdom=save_wisdom)
            sum_data, sum_randoms = np.sum(self.data_mesh.value), np.sum(self.randoms_mesh.value)
            alpha = sum_data * 1. / sum_randoms
            self.delta_mesh = self.data_mesh - alpha * self.randoms_mesh
            self.ran_min = ran_min * sum_randoms / self._size_randoms
            mask = self.randoms_mesh > self.ran_min
            self.delta_mesh[mask] /= alpha * self.randoms_mesh[mask]
            self.delta_mesh[~mask] = -3.0
        else:
            self.delta_mesh = self.data_mesh / np.mean(self.data_mesh) - 1.
        self.logger.info(f'Set density contrast in {time.time() - t0:.2f} seconds.')
        return self.delta_mesh

    def run(self,thres_mask=-2, thres_low=-1, thres_high=5, thres_bins=200):
        """
        Run the Minkowski functionals.

        Returns
        -------
        MFs3D : array_like
            3D Minkowski Functionals V_0, V_1, V_2, V_3.
        """
        t0 = time.time()
        self.thres_mask = thres_mask
        self.thres_low  = thres_low
        self.thres_high = thres_high
        self.thres_bins = thres_bins
        query_positions = self.get_query_positions(self.delta_mesh, method='lattice')
        self.delta_query = self.delta_mesh.read_cic(query_positions).reshape(
            (self.delta_mesh.nmesh[0], self.delta_mesh.nmesh[1], self.delta_mesh.nmesh[2]))
        mf = Mk.MFs(self.delta_mesh,self.data_mesh.cellsize[0],self.thres_mask,self.thres_low,self.thres_high,self.thres_bins)
        self.MFs = mf.MFs3D
        self.logger.info(f"Minkowski functionals elapsed in {time.time() - t0:.2f} seconds.")
        return self.MFs

    def plot_MFs(self,label="MFs",mf_cons=[1,10**3,10**5,10**7]):
        """
        Plot the Minkowski functionals
        """
        import matplotlib.pyplot as plt
        fig = plt.figure(constrained_layout=False,figsize=[10,10])
        spec = fig.add_gridspec(ncols=2, nrows=2, hspace=0.2, wspace=0.3)

        x   = np.linspace(self.thres_low,self.thres_high,num=self.thres_bins+1)
        ylabels = [r"$V_{0}$",
                   r"$V_{1}[10^{- "+str(int(np.log10(mf_cons[1])))+"}hMpc^{-1}]$",
                   r"$V_{2}[10^{- "+str(int(np.log10(mf_cons[2])))+"}(hMpc^{-1})^2]$",
                   r"$V_{3}[10^{- "+str(int(np.log10(mf_cons[3])))+"}(hMpc^{-1})^3]$"]
        
        for i in range(4):
            ii = i//2
            jj = i%2
            ax = fig.add_subplot(spec[ii,jj])
            ax.plot(x,self.MFs[:,i]*mf_cons[i],color="blue",label=label)
            if i==0:ax.legend()
            
            ax.set_xlabel(r"$\delta$")
            ax.set_ylabel(ylabels[i])
            ax.axhline(color="black")
            ax.set_xlim(self.thres_low,self.thres_high)
        
        return fig
