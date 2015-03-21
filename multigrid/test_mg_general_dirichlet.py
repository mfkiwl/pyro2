#!/usr/bin/env python

"""Test the general MG solver with Dirichlet boundary conditions.

Here we solve:

   alpha phi + div{beta grad phi} + gamma . grad phi = f

with

   alpha = 1.0
   beta = cos(2*pi*x)*cos(2*pi*y) + 2.0
   gamma_x = sin(2*pi*x)
   gamma_y = sin(2*pi*y)

   f = (-16.0*pi**2*cos(2*pi*x)*cos(2*pi*y) + 2.0*pi*cos(2*pi*x) + 
         2.0*pi*cos(2*pi*y) - 16.0*pi**2 + 1.0)*sin(2*pi*x)*sin(2*pi*y)

This has the exact solution:

   phi = sin(2.0*pi*x)*sin(2.0*pi*y)

on [0,1] x [0,1]

We use Dirichlet BCs on phi.  

For the coefficients we do not have to impose the same BCs, since that
may represent a different physical quantity.  beta is the one that
really matters since it must be brought to the edges.  Here we take
beta to have Neumann BCs.  (Dirichlet BCs for beta will force it to 0
on the boundary, which is not correct here)

"""

from __future__ import print_function

import os

import numpy as np
import matplotlib.pyplot as plt

import compare
import mesh.patch as patch
import general_MG as MG
from util import msg

# the analytic solution
def true(x,y):
    return np.sin(2.0*np.pi*x)*np.sin(2.0*np.pi*y)


# the coefficients
def alpha(x,y):
    return np.ones_like(x)

def beta(x,y):
    return 2.0 + np.cos(2.0*np.pi*x)*np.cos(2.0*np.pi*y)

def gamma_x(x,y):
    return np.sin(2*np.pi*x)

def gamma_y(x,y):
    return np.sin(2*np.pi*y)


# the L2 error norm
def error(myg, r):

    # L2 norm of elements in r, multiplied by dx to
    # normalize
    return np.sqrt(myg.dx*myg.dy*np.sum((r[myg.ilo:myg.ihi+1,
                                           myg.jlo:myg.jhi+1]**2).flat))


# the righthand side
def f(x,y):
    return (-16.0*np.pi**2*np.cos(2*np.pi*x)*np.cos(2*np.pi*y) +
            2.0*np.pi*np.cos(2*np.pi*x) + 2.0*np.pi*np.cos(2*np.pi*y) -
            16.0*np.pi**2 + 1.0)*np.sin(2*np.pi*x)*np.sin(2*np.pi*y)



def test_general_poisson_dirichlet(N, store_bench=False, comp_bench=False,
                                   make_plot=False):
    """
    test the general MG solver.  The return value
    here is the error compared to the exact solution, UNLESS
    comp_bench=True, in which case the return value is the
    error compared to the stored benchmark
    """

    # test the multigrid solver
    nx = N
    ny = nx


    # create the coefficient variable
    g = patch.Grid2d(nx, ny, ng=1)
    d = patch.CellCenterData2d(g)
    bc_c = patch.BCObject(xlb="neumann", xrb="neumann",
                          ylb="neumann", yrb="neumann")
    d.register_var("alpha", bc_c)
    d.register_var("beta", bc_c)
    d.register_var("gamma_x", bc_c)
    d.register_var("gamma_y", bc_c)
    d.create()

    a = d.get_var("alpha")
    a[:,:] = alpha(g.x2d, g.y2d)

    b = d.get_var("beta")
    b[:,:] = beta(g.x2d, g.y2d)

    gx = d.get_var("gamma_x")
    gx[:,:] = gamma_x(g.x2d, g.y2d)

    gy = d.get_var("gamma_y")
    gy[:,:] = gamma_y(g.x2d, g.y2d)

    
    # create the multigrid object
    a = MG.GeneralMG2d(nx, ny,
                       xl_BC_type="dirichlet", yl_BC_type="dirichlet",
                       xr_BC_type="dirichlet", yr_BC_type="dirichlet",
                       nsmooth=10,
                       nsmooth_bottom=50,
                       coeffs=d,
                       verbose=1, vis=0, true_function=true)


    # initialize the solution to 0
    a.init_zeros()

    # initialize the RHS using the function f
    rhs = f(a.x2d, a.y2d)
    a.init_RHS(rhs)

    # solve to a relative tolerance of 1.e-11
    a.solve(rtol=1.e-11)

    # alternately, we can just use smoothing by uncommenting the following
    #a.smooth(a.nlevels-1,50000)

    # get the solution
    v = a.get_solution()

    # compute the error from the analytic solution
    b = true(a.x2d,a.y2d)
    e = v - b

    enorm = error(a.soln_grid, e)
    print(" L2 error from true solution = %g\n rel. err from previous cycle = %g\n num. cycles = %d" % \
          (enorm, a.relative_error, a.num_cycles))


    # plot the solution
    if make_plot:
        plt.clf()

        plt.figure(figsize=(10.0,4.0), dpi=100, facecolor='w')

        plt.subplot(121)

        plt.imshow(np.transpose(v[a.ilo:a.ihi+1,a.jlo:a.jhi+1]),
                   interpolation="nearest", origin="lower",
                   extent=[a.xmin, a.xmax, a.ymin, a.ymax])

        plt.xlabel("x")
        plt.ylabel("y")

        plt.title("nx = {}".format(nx))

        plt.colorbar()


        plt.subplot(122)

        plt.imshow(np.transpose(e[a.ilo:a.ihi+1,a.jlo:a.jhi+1]),
                   interpolation="nearest", origin="lower",
                   extent=[a.xmin, a.xmax, a.ymin, a.ymax])

        plt.xlabel("x")
        plt.ylabel("y")

        plt.title("error")

        plt.colorbar()

        plt.tight_layout()

        plt.savefig("mg_general_dirichlet_test.png")

    # store the output for later comparison
    bench = "mg_general_poisson_dirichlet"
    bench_dir = os.environ["PYRO_HOME"] + "/multigrid/tests/"

    my_data = a.get_solution_object()
    
    if store_bench:
        my_data.write("{}/{}".format(bench_dir, bench))

    # do we do a comparison?
    if comp_bench:
        compare_file = "{}/{}".format(bench_dir, bench)
        msg.warning("comparing to: %s " % (compare_file) )
        bench_grid, bench_data = patch.read(compare_file)

        result = compare.compare(my_data.grid, my_data,
                                 bench_grid, bench_data)

        if result == 0:
            msg.success("results match benchmark\n")
        else:
            msg.warning("ERROR: " + compare.errors[result] + "\n")

        return result

    
    # normal return -- error wrt true solution
    return enorm


if __name__ == "__main__":

    N = [16, 32, 64] #, 128, 256, 512]
    err = []

    plot = False
    store = False
    do_compare = False
    
    for nx in N:
        if nx == max(N):
            plot = True
            #store = True
            #do_compare = True
            
        enorm = test_general_poisson_dirichlet(nx, make_plot=plot,
                                               store_bench=store, comp_bench=do_compare)
        
        err.append(enorm)


    # plot the convergence
    N = np.array(N, dtype=np.float64)
    err = np.array(err)

    plt.clf()
    plt.loglog(N, err, "x", color="r")
    plt.loglog(N, err[0]*(N[0]/N)**2, "--", color="k")

    plt.xlabel("N")
    plt.ylabel("error")

    f = plt.gcf()
    f.set_size_inches(7.0,6.0)

    plt.tight_layout()

    plt.savefig("mg_general_dirichlet_converge.png")
