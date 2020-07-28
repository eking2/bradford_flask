import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sympy import S, symbols, printing

cwd = Path().absolute()

class bradford_calc:

    def __init__(self, df, filename, poly=2):

        '''
        determine protein concentration from absorbance readings

        df : dataframe
            absorbances for standards and samples, and dilution factors
        poly : int
            polynomial degree to fit data to (default = 2)
        '''

        self.df = df
        self.filename = filename
        self.poly = poly

        self.std = None
        self.proteins = None

    def _subset_data(self):

        '''
        split abs into standard curve
        and sample absorbances
        '''

        std = self.df.query("Dil == 'std'")
        proteins = self.df.query("Dil != 'std'")

        # convert str to numeric
        std = std.assign(Sample = lambda x: pd.to_numeric(x['Sample']))

        return std, proteins

    def _fit_std_curve(self, std):

        '''
        fit standard curve to polynomial
        '''

        # fit
        p = np.poly1d(np.polyfit(std['abs_595'], std['Sample'], self.poly))

        # calc error and correlation in best fit curve to data
        residuals = std['Sample'] - p(std['abs_595'])
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((std['Sample'] - np.mean(std['Sample']))**2)
        r_sq = 1 - (ss_res / ss_tot)

        return p, r_sq

    def _plot_bradford(self, std, proteins, p, r_sq):

        '''
        plot bradford standard curve and sample absorbance data points
        '''

        # plot
        fig, ax = plt.subplots(figsize=(6,5))

        # standard curve and labeled points
        xra = np.linspace(std['abs_595'].min(), std['abs_595'].max(), 100)
        plt.plot(xra, p(xra), lw=2.5, color='orange', zorder=0)
        plt.scatter(std['abs_595'], std['Sample'], edgecolor='k', alpha=0.5,
                    label='BSA standards', marker='s')

        # plot replicates of each sample abs
        for samp in proteins['Sample'].unique():
            temp = proteins[proteins['Sample'] == samp]
            plt.scatter(temp['abs_595'], p(temp['abs_595']), label=samp, edgecolor='k', alpha=0.8)

        plt.grid(alpha=0.2)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='large')
        ax.set_axisbelow(True)

        # setup poly equation to pretty print
        x = symbols("x")

        # extract coefficients and reverse so order is decreasing powers
        poly = sum(S("{:6.1f}".format(v))*x**i for i, v in enumerate(p.c[::-1]))
        eq_latex = printing.latex(poly)

        annotation_str = '${}$'.format(eq_latex)
        annotation_str += '\n'
        annotation_str += r'$R^2$ = {:.3f}'.format(r_sq)

        plt.text(0.05, 0.8, annotation_str, transform=ax.transAxes, fontsize='large')
        plt.xlabel('OD595')
        plt.ylabel('Concentration (ug/mL)')
        plt.title('Bradford Assay Standard Curve')

        plt.savefig(Path(cwd, 'tmp', f'{self.filename}_std_curve.png'), bbox_inches='tight', dpi=300)


    def _calc_concs(self, p, proteins):

        '''
        calc final protein concentrations
        '''

        # correct for dilution factor in protein samples
        # convert to mg/ml
        proteins = proteins.assign(Dil = lambda x: pd.to_numeric(x['Dil']))
        proteins['conc_mg_ml'] = p(proteins['abs_595']) * proteins['Dil'] / 1000

        # avg results over all replicates
        grp = proteins.groupby('Sample')['conc_mg_ml'].agg([np.mean, np.std]).reset_index()

        # get stderror (in percent)
        # and concentrations after diluting with 20% glycerol for storage
        grp['stderr'] = grp['std']/grp['mean'] * 100
        grp = grp.rename(columns={'mean' : 'conc_mg_ml'})
        grp['after_glycerol_mg_ml'] = grp['conc_mg_ml']*0.6

        # clean up column names and save
        grp = grp.rename(columns = {'conc_mg_ml' : 'Conc (mg/ml)',
                                    'std' : 'STDEV',
                                    'stderr' : '% Standard Error',
                                    'after_glycerol_mg_ml' : 'Conc with 20% glycerol (mg/ml)'})

        grp.round(2).to_csv(Path(cwd, 'tmp', f'{self.filename}_concs.csv'), index=False)

        return grp.round(2)

    def run_all(self):

        # split data
        std, proteins = self._subset_data()

        # fit std curve
        p, r_sq = self._fit_std_curve(std)

        # plot
        self._plot_bradford(std, proteins, p, r_sq)

        # output results
        self._calc_concs(p, proteins)



