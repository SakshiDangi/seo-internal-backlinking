import { auth, clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/sign-in",
  "/sign-up",
  "/",
  "home",
  "pricing"
])
 
const isPublicApiRoute = createRouteMatcher([ 
  "/api/"
])

export default clerkMiddleware((auth, req) => {
  const {userId} = auth();
  const currentUrl = new URL(req.url)
  const isAccessingDashboard = currentUrl.pathname === "/"
  const isApiRequest = currentUrl.pathname.startsWith("/api")

  //user is logged in & accessing public routes but not dashboard
  if(userId && isPublicRoute(req) && !isAccessingDashboard) {
    return NextResponse.redirect(new URL("/", req.url))
  }
  //not logged in
  if(!userId){
    /// user trying to access(login) protected route
    if(!isPublicRoute(req) && !isPublicApiRoute(req)){
      return NextResponse.redirect(new URL("/sign-in", req.url))
    }

    /// if request is for protected API & user is not loggedin
    if(isApiRequest && !isPublicApiRoute(req)) {
      return NextResponse.redirect(new URL("/sign-in", req.url))
    }
  }
  return NextResponse.next()

});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!.*\\..*|_next).*)', "/", '/(api|trpc)(.*)'
  ],
};