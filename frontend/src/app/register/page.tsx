'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Car, Lock, Mail, User } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Alert, AlertDescription } from '@/components/ui/alert';

const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters."),
  email: z.string().email("Please enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
  password_confirmation: z.string()
}).refine((data) => data.password === data.password_confirmation, {
  message: "Passwords don't match.",
  path: ["password_confirmation"],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormValues) => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiFetch('/register', {
        method: 'POST',
        body: JSON.stringify(data)
      });
      
      if (res.ok) {
        const json = await res.json();
        localStorage.setItem('auth_token', json.token);
        router.push('/dashboard');
      } else {
        const err = await res.json();
        setError(err.message || 'Registration failed.');
      }
    } catch {
      setError('An error occurred during registration. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1549646452-32a26c48332d?auto=format&fit=crop&q=80')] bg-cover bg-center opacity-[0.03]"></div>
      
      <div className="w-full max-w-md relative z-10 animate-in zoom-in-95 duration-300">
        <div className="flex justify-center mb-6">
          <div className="bg-primary text-primary-foreground p-3 rounded-2xl shadow-lg flex items-center gap-2">
            <Car className="h-6 w-6" />
            <span className="font-bold tracking-tight">SmartPark</span>
          </div>
        </div>
        
        <Card className="border-0 shadow-xl overflow-hidden">
          <div className="h-2 w-full bg-gradient-to-r from-emerald-400 to-teal-500"></div>
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-2xl font-bold tracking-tight">Create Account</CardTitle>
            <CardDescription className="text-base">Register a new administrator account</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input 
                    id="name" 
                    placeholder="John Doe" 
                    className={`pl-10 ${errors.name ? 'border-red-500' : ''}`}
                    {...register('name')}
                  />
                </div>
                {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input 
                    id="email" 
                    type="email" 
                    placeholder="admin@smartpark.com" 
                    className={`pl-10 ${errors.email ? 'border-red-500' : ''}`}
                    {...register('email')}
                  />
                </div>
                {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input 
                      id="password" 
                      type="password" 
                      placeholder="••••••••" 
                      className={`pl-10 ${errors.password ? 'border-red-500' : ''}`}
                      {...register('password')}
                    />
                  </div>
                  {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password_confirmation">Confirm Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input 
                      id="password_confirmation" 
                      type="password" 
                      placeholder="••••••••" 
                      className={`pl-10 ${errors.password_confirmation ? 'border-red-500' : ''}`}
                      {...register('password_confirmation')}
                    />
                  </div>
                  {errors.password_confirmation && <p className="text-xs text-red-500 mt-1">{errors.password_confirmation.message}</p>}
                </div>
              </div>

              <Button type="submit" className="w-full bg-teal-600 hover:bg-teal-700 mt-4 h-11 shadow-sm text-md" disabled={isLoading}>
                {isLoading ? 'Creating account...' : 'Create Account'}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center border-t py-4 bg-slate-50/50">
            <p className="text-sm text-muted-foreground">
              Already have an account? <Link href="/login" className="text-teal-600 font-medium hover:underline">Sign In</Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
