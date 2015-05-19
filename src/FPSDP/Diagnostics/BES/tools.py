import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from scipy.interpolate import interp2d, splev, splrep
from scipy.fftpack import fft2, ifft2
import FPSDP.Diagnostics.Beam.beam as beam_
import FPSDP.Diagnostics.BES.bes as bes_

class Tools:
    """ Defines a few tools for doing some computations on the BES image
    
    Two different methods of initalization have been made:
    The first one is the usual __init__ function that take as input the photon radiance, the R,Z coordinates
    and the psin value, and the second one read a npz file with a standard order and calls the __init__ method.

    :param np.array[Nt,Nfib] I: Photon radiance
    :param np.array[Nfib] R: R coordinate
    :param np.array[Nfib] Z: Z coordinate
    :param np.array[Nfib] psin: :math:`\Psi_n` value
    :param bool I_fluc: Input are fluctuation or total intensity
    """

    def __init__(self,I,R,Z,psin,I_fluc=False):
        if I_fluc == False:
            Iav = np.mean(I,axis=0)
            self.I = (I-Iav)/Iav
        else:
            self.I = I

        self.R = R
        self.Z = Z
        self.psin = psin
        self.Nfoc = Z.shape[0]
        self.Nt = I.shape[0]

    @classmethod
    def init_from_file(cls,filename,fluc=False):
        """ Load of file in the numpy format (npz)

        The data inside it should be in the following order: [I,psin,pos_foc,...]

        :param str filename: Name of the file
        :param bool fluc: The intensity inside the file is the total (False) or the fluctuation (True)
        """
        data = np.load(filename)
        I = data['arr_0']
        psin = data['arr_1']
        pos = data['arr_2']
        R = np.sqrt(np.sum(pos[:,0:2]**2,axis=1))
        Z = pos[:,2]
        return cls(I,R,Z,psin,fluc)

    def interpolate(self,Nr,Nz,I):
        """ Interpolate all the data on a spatial mesh and create this mesh.
        The interpolation is done for each timestep
        """
        if not hasattr(self,'r'):
            self.r = np.linspace(np.min(self.R),np.max(self.R),Nr)
            self.z = np.linspace(np.min(self.Z),np.max(self.Z),Nz)
        else:
            if (self.r.shape[0] != Nr) or (self.z.shape[0] != Nz):
                raise NameError('Not the same size of mesh')

        Igrid = np.zeros((self.Nt,Nr,Nz))
        for i in range(self.Nt):
            temp = interp2d(self.R,self.Z,I[i,:])
            Igrid[i,:,:] = temp(self.r,self.z).T
            
        return Igrid

    def fluctuations_picture(self,timestep,v=40):
        """ Plot a graph of the fluctuation
        :param int timestep: Index of the timestep
        :param int v: Number of ticks for the colorbar
        """
        plt.figure()
        plt.tricontourf(self.R,self.Z,self.I[timestep,:],v)
        plt.colorbar()
        plt.plot(self.R,self.Z,'x')
        plt.tricontour(self.R,self.Z,self.psin,[1])
        plt.xlabel('R[m]')
        plt.ylabel('Z[m]')
        plt.show()

    def fluctuations_movie(self,v=40):
        """ Make a movie from the data and save them in movie.mp4
        :param int v: Number of ticks for the colorbar
        """        
        from matplotlib import animation
        fig = plt.figure()
        ax = plt.gca()

        plt.xlabel('R[m]')
        plt.ylabel('Z[m]')

        v = np.linspace(np.min(self.I),np.max(self.I),v)
        
        def animate(i):
            ax.cla()
            print 'Timestep: ', i
            plt.title('Timestep : {}'.format(i))
            plt.tricontourf(self.R,self.Z,self.I[i,:],v)
            plt.plot(self.R,self.Z,'x')
            plt.tricontour(self.R,self.Z,self.psin,[1])
            fig.canvas.draw()
            return None

        # call the animator.  blit=True means only re-draw the parts that have changed.
        anim = animation.FuncAnimation(fig, animate, frames=self.I.shape[0],repeat=False)
        
        # save the animation as an mp4.  This requires ffmpeg or mencoder to be
        # installed.  The extra_args ensure that the x264 codec is used, so that
        # the video can be embedded in html5.  You may need to adjust this for
        # your system: for more information, see
        # http://matplotlib.sourceforge.net/api/animation_api.html

        FFwriter = animation.FFMpegWriter()
        anim.save('movie.mp4', writer=FFwriter,fps=15, extra_args=['-vcodec', 'libx264'])

        
    def comparison_picture(self,tool2,timestep,v=40):
        """ Make a picture from the data of the fluctuation
        :param Tools tool2: Second instance of the Tools class
        :param int timestep: Index of the timestep
        :param int v: Number of ticks for the colorbar
        """        

        fig, axarr = plt.subplots(1,2,sharey=True)
        
        lim1 = np.min([np.max(self.I), -np.min(self.I)])
        lim2 = np.min([np.max(tool2.I), -np.min(tool2.I)])
        v1 = np.linspace(-lim1,lim1,v)
        v2 = np.linspace(-lim2,lim2,v)
        fig, axarr = plt.subplots(1,2)
        
        axarr[0].set_xlabel('R[m]')
        axarr[0].set_ylabel('Z[m]')
        axarr[1].set_xlabel('R[m]')

        
        tri0 = axarr[0].tricontourf(self.R,self.Z,self.I[0,:],v1)
        tri1 = axarr[1].tricontourf(tool2.R,tool2.Z,tool2.I[0,:],v2)

        cb = plt.colorbar(tri0,ax=axarr[0])
        cb = plt.colorbar(tri1,ax=axarr[1])


        axarr[0].locator_params(axis = 'x',nbins=5)
        
        axarr[1].locator_params(axis = 'x',nbins=5)
        axarr[0].set_title('Density fluctuation')
        axarr[1].set_title('Synthetic BES')
        
        axarr[1].set_yticklabels([])
        plt.suptitle('Timestep : {}'.format(timestep))
        
        axarr[0].plot(tool2.R,tool2.Z,'x')
        tri1 = axarr[0].tricontourf(tool2.R,tool2.Z,tool2.I[timestep,:],v2)
        axarr[0].tricontour(self.R,self.Z,self.psin,[1])
        
        axarr[1].plot(self.R,self.Z,'x')
        tri2 = axarr[1].tricontourf(self.R,self.Z,self.I[timestep,:],v1)
        axarr[1].tricontour(self.R,self.Z,self.psin,[1])
        
        plt.show()

    def comparison_movie(self,tool2,v=40):
        """ Make a movie from the data and save them in movie.mp4
        :param int timestep: Index of the timestep
        :param int v: Number of ticks for the colorbar
        """        
        from matplotlib import animation

        lim1 = np.min([np.max(self.I), -np.min(self.I)])
        lim2 = np.min([np.max(tool2.I), -np.min(tool2.I)])
        v1 = np.linspace(-lim1,lim1,v)
        v2 = np.linspace(-lim2,lim2,v)
        fig, axarr = plt.subplots(1,2)
        
        axarr[0].set_xlabel('R[m]')
        axarr[0].set_ylabel('Z[m]')
        axarr[1].set_xlabel('R[m]')

        
        tri0 = axarr[0].tricontourf(self.R,self.Z,self.I[0,:],v1)
        tri1 = axarr[1].tricontourf(tool2.R,tool2.Z,tool2.I[0,:],v2)

        cb = plt.colorbar(tri0,ax=axarr[0])
        cb = plt.colorbar(tri1,ax=axarr[1])


        def animate(i):
            print 'Timestep: ', i
            axarr[0].cla()
            axarr[0].locator_params(axis = 'x',nbins=5)
            axarr[1].cla()
            axarr[1].locator_params(axis = 'x',nbins=5)
            axarr[0].set_title('Density fluctuation')
            axarr[1].set_title('Synthetic BES')
  
            axarr[1].set_yticklabels([])
            plt.suptitle('Timestep : {}'.format(i))
            
            axarr[0].plot(tool2.R,tool2.Z,'x')
            tri1 = axarr[0].tricontourf(tool2.R,tool2.Z,tool2.I[i,:],v2,extend='both')
            axarr[0].tricontour(self.R,self.Z,self.psin,[1])

            axarr[1].plot(self.R,self.Z,'x')
            tri2 = axarr[1].tricontourf(self.R,self.Z,self.I[i,:],v1,extend='both')
            axarr[1].tricontour(self.R,self.Z,self.psin,[1])

            fig.canvas.draw()
            return None

        # call the animator.  blit=True means only re-draw the parts that have changed.
        anim = animation.FuncAnimation(fig, animate, frames=self.I.shape[0],repeat=False)
        
        # save the animation as an mp4.  This requires ffmpeg or mencoder to be
        # installed.  The extra_args ensure that the x264 codec is used, so that
        # the video can be embedded in html5.  You may need to adjust this for
        # your system: for more information, see
        # http://matplotlib.sourceforge.net/api/animation_api.html

        FFwriter = animation.FFMpegWriter()
        anim.save('movie.mp4', writer=FFwriter,fps=15, extra_args=['-vcodec', 'libx264'])


    def crosscorrelation(self, Nr=60, Nz=70, dr_max=0.05, dz_max=0.03, dkr_max=300, dkz_max=300, graph='3d'):
        """
        """
        from scipy.signal import correlate2d
        from mpl_toolkits.mplot3d import Axes3D

        corr = np.zeros(2*np.array([Nr,Nz])-1)
        
        Igrid = self.interpolate(Nr,Nz,self.I)
            
        for i in range(self.Nt):
            if np.isfinite(Igrid[i,...]).all():
                corr += correlate2d(Igrid[i,...],Igrid[i,...])
            else:
                print 'miss'


        corr /= np.max(corr)
        temp = np.zeros(2*Nr-1)
        r = self.r-self.r[0]
        z = self.z-self.z[0]
        temp[:Nr-1] = -r[Nr-1:0:-1]
        temp[Nr-1:] = r
        r = temp
        temp = np.zeros(2*Nz-1)
        temp[:Nz-1] = -z[Nz-1:0:-1]
        temp[Nz-1:] = z
        z = temp

        indr_ = (r >= 0) & (r<dr_max)
        indz_ = (z >= 0) & (z<dz_max)
        ind = np.einsum('i,j->ij',indr_,indz_)
        
        rm, zm = np.meshgrid(r[indr_],z[indz_])
        fft_corr = np.abs(np.fft.fft2(corr))/np.sqrt(Nr*Nz)
        corr = corr[ind]
        corr = np.reshape(corr,[np.sum(indr_),np.sum(indz_)])
        
        krfft = np.fft.fftfreq(Nr,r[2]-r[1])
        kzfft = np.fft.fftfreq(Nz,z[2]-z[1])
        indrfft = (krfft >= 0) & (krfft < dkr_max)
        indzfft = (kzfft >= 0) & (kzfft < dkz_max)
        krfft,kzfft = np.meshgrid(krfft[indrfft],kzfft[indzfft])
        
        fig = plt.figure()
        plt.title('Correlation')
        if graph == '3d':
            ax = fig.gca(projection='3d')
            surf = ax.plot_surface(rm,zm,corr.T, cmap=matplotlib.cm.coolwarm, rstride=2, linewidth=0, cstride=2)
            fig.colorbar(surf)
        else:
            plt.contourf(r[indr_],z[indz_],corr.T,30)
            plt.colorbar()
        plt.xlabel('R')
        plt.ylabel('Z')

        fft_ = fft_corr[indrfft,:]
        fft_ = fft_[:,indzfft]
        
        fig = plt.figure()
        plt.title('FFT of the Correlation')
        if graph == '3d':
            ax = fig.gca(projection='3d')
            surf = ax.plot_surface(krfft,kzfft,fft_.T, cmap=matplotlib.cm.coolwarm,rstride=1,linewidth=0, cstride=1)
            fig.colorbar(surf)
        else:
            plt.contourf(krfft,kzfft,fft_.T,40)
            plt.colorbar()
        plt.xlabel('k_r')
        plt.ylabel('k_z')
            
        plt.figure()
        plt.plot(r[indr_],corr[:,0],label='R')
        plt.plot(z[indz_],corr[0,:],label='Z')
        plt.legend()
        
        plt.show()

    def radial_dep_correlation(self,Nr=40,Zref=0.01,eps=0.4,figure=True):
        """
        """
        ind = np.abs((self.Z - Zref)/Zref) < eps
        N = np.sum(ind)
        print N
        
        corr = np.zeros(Nr)
        r = np.linspace(np.min(self.R[ind]),np.max(self.R[ind]),Nr)

        R_temp = self.R[ind]
        Igrid = np.zeros((self.Nt,Nr))
        for i in range(self.Nt):
            temp = splrep(R_temp,self.I[i,ind])
            Igrid[i,:] = splev(r,temp)
        
        for i in range(Nr):
            temp = np.zeros(Nr)
            for j in range(Nr):
                temp[j] = np.corrcoef(Igrid[:,i],Igrid[:,j])[0,1]
            temp = r[(temp<np.exp(-1)) & (r>r[i])]-r[i]
            if temp.shape[0] > 0:
                corr[i] = temp[0]
            else:
                corr[i] = np.nan
        if not figure:
            return r,corr

        fig = plt.figure()
        plt.plot(r,corr)
        plt.xlabel('R [m]')
        plt.ylabel('Correlation length')
        plt.show()
            
    def computePSF(self, ne, Nr=20, Nz=30, ne_fluc=False):
        """ Compute the PSF
        """
        if isinstance(ne,str):
            data = np.load(ne)
            ne = data['arr_0']
        if ne_fluc == False:
            neav = np.mean(ne,axis=0)
            ne = (ne-neav)/neav

        negrid = self.interpolate(Nr,Nz,ne)
        Igrid = self.interpolate(Nr,Nz,self.I)
        
        self.psf = np.zeros((Nr,Nz))

        for i in range(self.Nt):
            ne_tilde = fft2(negrid[i,...])
            I_tilde = fft2(Igrid[i,...])
            I_tilde /= ne_tilde
            self.psf += np.real(ifft2(I_tilde))

        self.psf /= self.Nt

        plt.figure()
        plt.contourf(self.r,self.z,self.psf.T)
        plt.xlabel('R[m]')
        plt.ylabel('Z[m]')
        plt.colorbar()
        plt.show()

        
""" Define a few test for checking the data given by the code
It contains all the code used for the figure in my report
"""
name = 'FPSDP/Diagnostics/BES/bes.in'
t = 150


def beam_density():
    """ Compare the beam density of the equilibrium case and of the equilibrium+fluctuations case

    """
    bes = bes_.BES(name)
    bes.beam.eq = True
    bes.beam.t_ = t-1 # will be increase in compute_beam_on_mesh
    bes.beam.data.current = t
    bes.beam.data.load_next_time_step(increase=False)
    bes.beam.compute_beam_on_mesh()
    nb_eq = bes.beam.density_beam
    ne_eq = bes.beam.get_quantities(bes.beam.mesh,t,['ne'],True,check=False)[0]
    bes.beam.eq = False
    
    bes.beam.t_ = t-1 # will be increase in compute_beam_on_mesh
    bes.beam.compute_beam_on_mesh()
    nb_fl = bes.beam.density_beam
    ne_fl = bes.beam.get_quantities(bes.beam.mesh,t,['ne'],False,check=False)[0]
    dl = np.sqrt(np.sum((bes.beam.mesh-bes.beam.pos[np.newaxis,:])**2,axis=1))
    
    
    fig, axarr = plt.subplots(2,sharex=True)
        
    axarr[1].plot(dl,((nb_eq-nb_fl)/nb_eq).T)
    plt.xlabel('Distance [m]')
    axarr[1].set_ylabel('Error')
    axarr[1].legend(['1st component','2nd component','3rd component'],loc=4)
    axarr[1].grid(True)
    
    axarr[0].plot(dl,nb_eq.T)
    axarr[0].plot(dl,nb_fl.T)
    axarr[0].grid(True)
    axarr[0].set_ylabel('Beam density [m$^{-3}$]')
    axarr[0].legend(['1st Eq','2nd Eq','3rd Eq'])
    
    
    fig, axarr = plt.subplots(2,sharex=True)
        
    axarr[1].plot(dl,((ne_eq-ne_fl)/ne_eq))
    plt.xlabel('Distance [m]')
    axarr[1].set_ylabel('Error')
    axarr[1].grid(True)
    
    axarr[0].plot(dl,ne_eq)
    axarr[0].plot(dl,ne_fl)
    axarr[0].grid(True)
    axarr[0].legend(['Equilibrium','Fluctuations'],loc=4)
    axarr[0].set_ylabel('Electron Density [m$^{-3}$]')
        
    plt.figure()
    tot = np.sum(nb_eq,axis=0)
    plt.plot(dl,(nb_eq/tot[np.newaxis,:]).T)
    tot = np.sum(nb_fl,axis=0)
    plt.plot(dl,(nb_fl/tot[np.newaxis,:]).T)
    plt.legend(['1st Eq','2nd Eq','3rd Eq'],loc=2)
    plt.grid(True)
    
    plt.show()

def beam_emission():
    """ Shows the effect of the beam density on the emission and the effect of the lifetime.
    """
    bes = bes_.BES(name)
    bes.beam.t_ = t-1 # will be increase in compute_beam_on_mesh
    bes.beam.data.current = t
    bes.beam.data.load_next_time_step(increase=False)
    bes.beam.compute_beam_on_mesh()

    r_max = 0.25
    dl = np.sqrt(np.sum((bes.beam.mesh-bes.beam.pos[np.newaxis,:])**2,axis=1))
    Nr = 20
    r = np.linspace(-r_max,r_max,Nr)
    R,L = np.meshgrid(r,dl)
    R = R.flatten()
    L = L.flatten()
    perp = np.copy(bes.beam.direc)
    perp[0] = perp[1]
    perp[1] = -bes.beam.direc[0]
    pos = bes.beam.pos[np.newaxis,:] + L[:,np.newaxis]*bes.beam.direc + R[:,np.newaxis]*perp
    emis = bes.beam.get_emis(pos,t)[0,:]
    emis_l = bes.beam.get_emis_lifetime(pos,t)[0,:]

    emis = np.reshape(emis, (-1,Nr))
    emis_l = np.reshape(emis_l, (-1,Nr))
    R = np.reshape(R, (-1,Nr))
    L = np.reshape(L, (-1,Nr))

    v = 50
    plt.figure()
    plt.title('Photon radiance')
    plt.contourf(R,L,emis,v)
    width = bes.beam.stddev_h
    plt.plot([-width, -width],[0, dl[-1]],'--k')
    plt.plot([width, width],[0, dl[-1]],'--k')
    plt.colorbar()
    plt.xlabel('Distance from the central line [m]')
    plt.ylabel('Distance from the source [m]')

    plt.figure()
    plt.title('Photon radiance')
    plt.contourf(R,L,emis_l,v)
    plt.plot([-width, -width],[0, dl[-1]],'--k')
    plt.plot([width, width],[0, dl[-1]],'--k')
    plt.colorbar()
    plt.xlabel('Distance from the central line [m]')
    plt.ylabel('Distance from the source [m]')

    plt.figure()
    plt.title('Difference between the instantaneous and non-instantaneous emission')
    plt.contourf(R,L,(emis_l-emis)/emis,v)
    plt.plot([-width, -width],[0, dl[-1]],'--k')
    plt.plot([width, width],[0, dl[-1]],'--k')
    plt.colorbar()
    plt.xlabel('Distance from the central line [m]')
    plt.ylabel('Distance from the source [m]')

    plt.show()
