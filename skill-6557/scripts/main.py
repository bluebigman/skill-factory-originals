#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import math
import random

def solve_quadratic(a, b, c):
    """
    Solve quadratic equation ax^2 + bx + c = 0
    Returns (num_roots, roots) where roots is a list
    """
    if abs(a) < 1e-10:
        # Linear equation bx + c = 0
        if abs(b) < 1e-10:
            if abs(c) < 1e-10:
                return (float('inf'), [])  # Infinite solutions
            else:
                return (0, [])  # No solution
        else:
            return (1, [-c/b])
    
    discriminant = b*b - 4*a*c
    
    if discriminant > 1e-10:
        sqrt_disc = math.sqrt(discriminant)
        x1 = (-b + sqrt_disc) / (2*a)
        x2 = (-b - sqrt_disc) / (2*a)
        return (2, [x1, x2])
    elif abs(discriminant) <= 1e-10:
        x = -b / (2*a)
        return (1, [x])
    else:
        return (0, [])

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        # Self-test with known examples
        test_cases = [
            (1, -3, 2),  # x^2 - 3x + 2 = 0 -> x = 1, 2
            (1, -2, 1),  # x^2 - 2x + 1 = 0 -> x = 1 (double root)
            (1, 0, 1),   # x^2 + 1 = 0 -> no real roots
            (0, 2, -4),  # 2x - 4 = 0 -> x = 2
            (0, 0, 5),   # 5 = 0 -> no solution
            (0, 0, 0),   # 0 = 0 -> infinite solutions
        ]
        
        all_passed = True
        
        for a, b, c in test_cases:
            num_roots, roots = solve_quadratic(a, b, c)
            
            if a == 1 and b == -3 and c == 2:
                # x^2 - 3x + 2 = 0
                assert num_roots == 2, f"Expected 2 roots for x^2-3x+2, got {num_roots}"
                assert len(roots) == 2, f"Expected 2 roots, got {len(roots)}"
                # Roots should be close to 1 and 2
                roots_sorted = sorted(roots)
                assert abs(roots_sorted[0] - 1) < 0.01, f"Root 1 incorrect: {roots_sorted[0]}"
                assert abs(roots_sorted[1] - 2) < 0.01, f"Root 2 incorrect: {roots_sorted[1]}"
                
            elif a == 1 and b == -2 and c == 1:
                # x^2 - 2x + 1 = 0
                assert num_roots == 1, f"Expected 1 root for x^2-2x+1, got {num_roots}"
                assert len(roots) == 1, f"Expected 1 root, got {len(roots)}"
                assert abs(roots[0] - 1) < 0.01, f"Root incorrect: {roots[0]}"
                
            elif a == 1 and b == 0 and c == 1:
                # x^2 + 1 = 0
                assert num_roots == 0, f"Expected 0 roots for x^2+1, got {num_roots}"
                assert len(roots) == 0, f"Expected 0 roots, got {len(roots)}"
                
            elif a == 0 and b == 2 and c == -4:
                # 2x - 4 = 0
                assert num_roots == 1, f"Expected 1 root for 2x-4, got {num_roots}"
                assert len(roots) == 1, f"Expected 1 root, got {len(roots)}"
                assert abs(roots[0] - 2) < 0.01, f"Root incorrect: {roots[0]}"
                
            elif a == 0 and b == 0 and c == 5:
                # 5 = 0
                assert num_roots == 0, f"Expected 0 roots for 5=0, got {num_roots}"
                assert len(roots) == 0, f"Expected 0 roots, got {len(roots)}"
                
            elif a == 0 and b == 0 and c == 0:
                # 0 = 0
                assert num_roots == float('inf'), f"Expected infinite roots for 0=0, got {num_roots}"
                assert len(roots) == 0, f"Expected 0 roots, got {len(roots)}"
            
            print(f"Test case ({a}, {b}, {c}): {num_roots} roots, roots = {roots}")
        
        print("\nAll tests passed!")
        return 0
    else:
        # Interactive mode
        print("Quadratic Equation Solver: ax^2 + bx + c = 0")
        try:
            a = float(input("Enter a: "))
            b = float(input("Enter b: "))
            c = float(input("Enter c: "))
        except ValueError:
            print("Error: Please enter valid numbers")
            return 1
        
        num_roots, roots = solve_quadratic(a, b, c)
        
        if num_roots == float('inf'):
            print("Infinite solutions (identity)")
        elif num_roots == 0:
            print("No real solutions")
        elif num_roots == 1:
            print(f"One real solution: x = {roots[0]:.6f}")
        else:
            print(f"Two real solutions: x1 = {roots[0]:.6f}, x2 = {roots[1]:.6f}")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())
