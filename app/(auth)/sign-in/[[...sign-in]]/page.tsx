import { Register } from '@/components/register'
import { SignIn } from '@clerk/nextjs'

export default function Page() {
  return (
  <div>
  <Register />
  <SignIn />
  </div>
  )
}