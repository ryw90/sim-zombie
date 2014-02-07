import BeautifulSoup
import numpy as np
import pandas as pd

# Fixed parameters / initial conditions
num_humans = 10000
num_zombies = 50
pr_nat_death = .01 # Probability of natural death
pr_conv_zombie = .75 # Probability of converting human to zombie in encounter
pr_reanimate = .25 # Probability of reanimation
birth_rate = pr_nat_death * 1.25

def heat_map(svg_path, data): # 8 color classes  
    # Load the SVG map
    svg = open(svg_path, 'r')
 
    # Load into Beautiful Soup
    soup = BeautifulSoup(svg.read(), selfClosingTags=['defs','sodipodi:namedview'])
 
    # Find locations
    paths = soup.findAll('path')
 
    # Map colors (from ColorBrewer)
    colors = ["#FFF7FB", "#ECE7F2", "#D0D1E6", "#A6BDDB", "#74A9CF", "#3690C0", "#0570B0", "#034E7B"]
 
    # County style
    path_style = 'font-size:12px;fill-rule:nonzero;stroke:#000000;stroke-opacity:1;stroke-width:0.2;stroke-miterlimit:4;stroke-dasharray:none;stroke-linecap:butt;marker-start:none;stroke-linejoin:bevel;fill:'
 
    # Color the counties based on unemployment rate
    for p in paths:
    
        if p['id'] not in ["State_Lines", "separator"]:
            # pass
            try:
                rate = data[p['id']]
            except:
                continue
    
            if rate > .875: # TODO: recode using cut
                color_class = 7
            elif rate > .75:
                color_class = 6
            elif rate > .625:
                color_class = 5
            elif rate > .5:
                color_class = 4
            elif rate > .375:
                color_class = 3
            elif rate > .25:
                color_class = 2
            elif rate > .125:
                color_class = 1
            else:
                color_class = 0
    
            color = colors[color_class]
            p['style'] = path_style + color
    
    svg.close()            
    return soup.prettify()

class World:
    def __init__(self, num_humans, num_zombies):
        self.population = ['Z'] * num_zombies + ['H'] * num_humans
        self.period = 0
        
    def __str__(self):
        return str(pd.value_counts(self.population))
        
    def simulate(self, log=False):
        if log:
            print 'Now simulating period ' + str(self.period)
        counts = pd.value_counts(self.population)
        if 'H' not in counts:
            print 'Period ' + str(self.period) + ': Humans are now extinct!'
            return
        interact_rate = float(counts['H']) / (counts['H'] + counts['Z'])
        self.period += 1
                
        for i in range(0, len(self.population)): # Simulate interactions between humans, zombies, and the dead
            agent = self.population[i]
            if agent == 'H':
                    if np.random.rand() < pr_nat_death: # Humans die =[
                        self.population[i] = 'D'                       
            elif agent == 'Z':
                if np.random.rand() < interact_rate: # Zombies attack humans
                    if np.random.rand() < pr_conv_zombie: # Sometimes they convert them to zombies
                        try: 
                            self.population[self.population.index('H')] = 'Z'
                        except:
                            pass
                    else: # Othertimes they get killed
                        self.population[i] = 'D'
                else:
                    pass                   
            elif agent == 'D': # The dead reanimate
                if np.random.rand() < pr_reanimate:
                    self.population[i] = 'Z'
                else:
                    pass
        
        born = int(counts['H'] * birth_rate)
        self.population = self.population + ['H'] * born # People reproduce

if __name__=='__main__':        
    # Simple analysis
    world = World(num_humans, num_zombies) # initialize simulation
    results = list()
    results.append(dict(pd.value_counts(world.population)))
    
    for i in range(0,10):
        world.simulate()
        results.append(dict(pd.value_counts(world.population)))
    
    # A model with... quarantine?
    # Now allow "worlds" to interact (in every period, there is a chance that zombies escape state e.g. quarantine/tear down walls)
    census = pd.read_csv('NST_EST2012_ALLDATA.csv')
    neighbors = pd.read_csv('us_state_neighbors.csv', names=['id','neighbors'])
    neighbors.neighbors = neighbors.neighbors.apply(lambda x: x.split(','))
    
    states = census[pd.notnull(census['id'])][['id','CENSUS2010POP']]
    states = pd.merge(states, neighbors)
    states = states.set_index('id')
    
    states.CENSUS2010POP /= pow(10,3)
    states['zworld'] = [World(pop, 0) for pop in states.CENSUS2010POP.values]
    states.zworld[12] = World(states.CENSUS2010POP[12] - 50, 50) # Add zombies to IL
    
    t = 0
    for i in range(0,20): # Simulate
        ix_infected = states.index[states.zworld.apply(lambda x: 'Z' in pd.value_counts(x.population).index)]
        for ix_state in ix_infected:
            # ix_state = 'IL' 
            states.zworld[ix_state].simulate()
            print 'Simulated the state of ' + ix_state
            counts = pd.value_counts(states.zworld[ix_state].population)
            try:
                transmit_rate = counts['Z'] / (counts['Z'] + counts['H']) + .35
            except:
                transmit_rate = 1
            ix_transmitted = [states.neighbors[ix_state][key] for key, val in enumerate(np.random.rand(len(states.neighbors[ix_state]))) if val < transmit_rate]
            for ix_next_state in ix_transmitted:
                try:
                    states.zworld[ix_next_state].population[states.zworld[ix_next_state].population.index('H')] = 'Z'
                    print ix_next_state + ' has been infected!'                
                except:
                    pass        
                    
        # output as heat map
        data = states.zworld.apply(lambda x: pd.value_counts(x.population)).fillna(0) # prepare zombie data
        data['zombie_ratio'] = data['Z'] / (data['H'] + data['Z'])
        data = data['zombie_ratio']
        
        bob = open('outbreak/zombies_%d.svg'%(t), 'wb')
        bob.write(heat_map('states.svg', data))
        bob.close()
        t += 1
    
    # TO DO: Fix bug -- uninfected states aren't experiencing birth/death


        