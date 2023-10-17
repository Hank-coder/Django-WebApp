import numpy as np
import matplotlib.pyplot as plt

fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection='3d')

# Create a grid of points
x = np.linspace(-2, 2, 100)
y = np.linspace(-2, 2, 100)
X, Y = np.meshgrid(x, y)

# Compute Z values for each equation
Z1 = np.sqrt(X**2 + Y**2 + 2)  # for x^2 + y^2 + z^2 - 2 = 0
Z2 = np.sqrt(X**2 + Y**2 + 2)  # for x^2 + y^2 - z^2 - 2 = 0

# Plot the surfaces
ax.plot_surface(X, Y, Z1, alpha=0.5, rstride=100, cstride=100)
ax.plot_surface(X, Y, -Z1, alpha=0.5, facecolors='g', rstride=100, cstride=100)
ax.plot_surface(X, Y, Z2, alpha=0.5, facecolors='r', rstride=100, cstride=100)

# Setting labels and title
ax.set_xlabel('X axis')
ax.set_ylabel('Y axis')
ax.set_zlabel('Z axis')
ax.set_title('Comparison of Surfaces')

plt.show()
